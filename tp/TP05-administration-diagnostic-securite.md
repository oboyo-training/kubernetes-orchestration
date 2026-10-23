# TP05 — Diagnostiquer une panne et vérifier les accès

## Objectif

Utiliser les commandes de base pour trouver la cause d’un problème, corriger la configuration, puis vérifier les droits d’accès d’un compte de service.

## Prérequis

- TP03 terminé ; l’application fonctionne dans `kube-training`.
- TP04 terminé.
- Le cluster Kind est démarré.

## Partie A — Diagnostiquer un problème de Service

1. Vérifiez l’état de l’application :

```bash
kubectl -n kube-training get deployment,pods,svc,endpoints
```

2. Ouvrez `manifests/30-service.yaml`. Dans une copie nommée `/tmp/service-tp05.yaml`, remplacez temporairement `targetPort: http` par `targetPort: 8080`.

3. Appliquez la copie de test :

```bash
kubectl apply -f /tmp/service-tp05.yaml
kubectl -n kube-training get svc,endpoints
```

Cette fois, le Service a toujours des endpoints et les Pods sont `Ready`, mais la connexion échoue : le Service envoie le trafic vers le port 8080 du Pod, alors que l’application écoute sur le port 5000. Comparez avec le TP02 : là-bas, les endpoints étaient vides parce que le selector ne correspondait à aucun Pod.

```bash
kubectl -n kube-training get endpoints flask-app
kubectl -n kube-training port-forward svc/flask-app 8080:80
curl -i http://127.0.0.1:8080/health
```

Le test HTTP échoue malgré la présence d’endpoints. Arrêtez le `port-forward` avec `Ctrl+C`. Pour comprendre le routage, retrouvez les labels des Pods et la configuration du Service :

```bash
kubectl -n kube-training get pods --show-labels
kubectl -n kube-training describe svc flask-app
```

4. Avant de restaurer, regardez précisément ce que la panne a changé :

```bash
kubectl -n kube-training get endpoints flask-app
```

Les adresses des Pods sont bien là, mais le port annoncé est `8080`. Les
endpoints n’ont jamais disparu : c’est la cible qui est fausse. Restaurez
maintenant le Service depuis le manifeste d’origine :

```bash
kubectl apply -f manifests/30-service.yaml
kubectl -n kube-training get endpoints flask-app
```

Le port annoncé redevient `5000`. Retenez les deux formes de panne : au TP02,
aucun endpoint parce que le selector ne trouvait aucun Pod ; ici, des endpoints
présents mais qui visent un port sur lequel personne n’écoute.

## Partie B — Utiliser les outils de diagnostic

Exécutez les commandes et identifiez ce que chacune apporte :

```bash
kubectl -n kube-training get pods
kubectl -n kube-training describe pod <nom-du-pod>
kubectl -n kube-training logs <nom-du-pod>
kubectl -n kube-training get events --sort-by=.lastTimestamp
kubectl -n kube-training exec deployment/flask-app -- printenv APP_ENV
```

Remplacez `<nom-du-pod>` par un nom de Pod existant. Si un conteneur a redémarré, `kubectl logs <nom-du-pod> --previous` permet de consulter les logs du conteneur précédent.

## Partie C — Vérifier les droits avec RBAC

RBAC permet de définir ce qu’un compte a le droit de faire dans Kubernetes. Nous allons autoriser un compte de service à lire les ConfigMaps du namespace `kube-training`.

Créez les ressources :

```bash
kubectl -n kube-training create serviceaccount lecteur-config
```

Créez le fichier `/tmp/role-tp05.yaml` :

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: lecture-configmaps
  namespace: kube-training
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: lecteur-config-binding
  namespace: kube-training
subjects:
  - kind: ServiceAccount
    name: lecteur-config
    namespace: kube-training
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: lecture-configmaps
```

Appliquez le fichier et vérifiez les droits :

```bash
kubectl apply -f /tmp/role-tp05.yaml
kubectl auth can-i get configmaps -n kube-training --as=system:serviceaccount:kube-training:lecteur-config
kubectl auth can-i delete pods -n kube-training --as=system:serviceaccount:kube-training:lecteur-config
```

Résultat attendu : la première commande répond `yes`, la seconde `no`. Le compte ne reçoit que les droits définis dans le Role.

## Partie D — Comprendre les limites de la sécurité réseau

Une NetworkPolicy peut limiter les flux entre Pods, mais son effet dépend du plugin réseau (CNI) qui équipe le cluster. Dans ce lab, ne concluez pas qu’un flux est bloqué simplement parce qu’un manifeste NetworkPolicy est accepté par l’API.

Répondez à ces questions :
- Quel risque réduit une NetworkPolicy ?
- Pourquoi faut-il vérifier que le CNI applique les règles ?
- Pourquoi un Secret Kubernetes ne doit-il pas être commité dans Git ?
- Pourquoi faut-il limiter les droits RBAC au strict nécessaire ?

## Partie E — Observer l’état des nœuds et la supervision

Kubernetes expose l’état de chaque nœud et les événements récents. Utilisez ces commandes :

```bash
kubectl get nodes
kubectl describe node <nom-du-worker>
kubectl get events -A --field-selector type=Warning
```

Remplacez `<nom-du-worker>` par le nom d’un nœud. Dans la sortie de `describe node`, repérez la section `Conditions` et les événements. Les conditions indiquent si le nœud est prêt et si certains problèmes sont détectés.

**Node Problem Detector** est un composant qui surveille le nœud lui-même, par exemple le noyau, le disque ou le runtime des conteneurs. Il remonte les problèmes détectés sous forme de conditions et d’événements Kubernetes. Il n’est pas installé dans ce lab.

**Google Cloud Operations** (anciennement Stackdriver) est un exemple d’outillage de supervision proposé par un fournisseur cloud. Il peut centraliser les journaux, les métriques et les alertes d’un environnement cloud. Il n’est pas installé dans ce lab.

Distinguez ces quatre notions :

- **Logs** : messages émis par une application ou un composant.
- **Événements** : faits ponctuels enregistrés par Kubernetes, par exemple un échec de scheduling.
- **Métriques** : mesures numériques suivies dans le temps, comme l’utilisation CPU ou mémoire.
- **Alertes** : notifications déclenchées lorsqu’une règle ou un seuil est atteint.

Vous avez déjà manipulé les trois premières : les logs et les événements dans la
partie B de ce TP, les métriques au TP04 avec `metrics-server`.
Relisez-les une dernière fois sur l’ensemble du cluster :

```bash
kubectl top nodes
kubectl top pods -A --sort-by=cpu
```

Si ces commandes répondent `error: Metrics API not available`, ne concluez pas
 tout de suite que `metrics-server` est absent. Vérifiez dans cet ordre :

```bash
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl -n kube-system get pods -l k8s-app=metrics-server
kubectl -n kube-system logs -l k8s-app=metrics-server --tail=20
```

- Si l’APIService n’existe pas, `metrics-server` n’est pas installé : reprenez la partie C du TP04.
- S’il existe mais affiche `AVAILABLE=False`, le déploiement n’est pas encore prêt, ou il n’a pas réussi à interroger les kubelets. Les logs le disent.
- S’il vient d’être installé, laissez passer une minute : la fenêtre de mesure doit se remplir.

Notez aussi ce que `metrics-server` n’est pas : il sert la consommation du
moment à `kubectl top` et à l’autoscaling. Il ne conserve aucun historique et
ne déclenche aucune alerte.

Les alertes sont la seule des quatre notions que nous n’installons pas. Elles
supposent un système qui conserve les métriques dans le temps et qui évalue des
règles, par exemple Prometheus avec Alertmanager.

## Nettoyage

Supprimez les ressources RBAC créées pour ce TP :

```bash
kubectl -n kube-training delete rolebinding lecteur-config-binding
kubectl -n kube-training delete role lecture-configmaps
kubectl -n kube-training delete serviceaccount lecteur-config
rm -f /tmp/role-tp05.yaml /tmp/service-tp05.yaml
```

## À retenir

- Pour diagnostiquer : vérifiez l’état, les événements, la description de la ressource et les logs. Formulez une hypothèse, corrigez un seul élément, puis vérifiez le résultat.
- Un Service sans endpoints et un Service avec des endpoints qui ne répond pas sont deux pannes différentes : la première vient du selector, la seconde du port visé sur le Pod.
- Un Role définit des droits dans un namespace ; un RoleBinding les attribue à un compte.
- `kubectl auth can-i` répond sans qu’il soit nécessaire de tenter l’action.
- L’effet réel d’une NetworkPolicy dépend du CNI : un manifeste accepté par l’API ne prouve pas que le flux est bloqué.

- Les métriques ne sont pas fournies par Kubernetes seul : il faut installer un composant qui les collecte, ici `metrics-server`.

## Questions

1. Au TP02, pourquoi le Service n’avait-il plus d’endpoints alors que les Pods étaient Ready ?
2. Pourquoi un Service qui a des endpoints peut-il quand même ne pas répondre ?
3. Quelle différence entre `get`, `describe`, `logs` et `exec` ?
4. À quoi servent Role et RoleBinding ?
5. Pourquoi la commande `kubectl auth can-i` est-elle utile ?
6. Pourquoi faut-il tester l’effet d’une NetworkPolicy sur un CNI qui la prend en charge ?
7. Quelle différence entre logs, événements, métriques et alertes ?
8. Quel type de problème Node Problem Detector peut-il signaler ?


---

**Suite :** [TP06 — Exposer l’application avec Gateway API](TP06-gateway-api.md)
