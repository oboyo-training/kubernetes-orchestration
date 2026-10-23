# TP04 — Configurer l’application et comprendre ses ressources

## Objectif

Modifier la configuration de l'application, lire ses requests/limits, tester le placement d’un Pod, puis mettre à jour l’application et revenir à la version précédente. Le montage d’un volume emptyDir est proposé en option.

## Prérequis

- TP03 terminé.
- Le Deployment `flask-app` fonctionne dans le namespace `kube-training`.
- Travaillez depuis la racine du dépôt.

## Partie A — Modifier la configuration avec ConfigMap

Affichez le ConfigMap et la configuration actuelle :

```bash
kubectl -n kube-training get configmap flask-app-config -o yaml
kubectl -n kube-training get pods
```

Ouvrez `manifests/10-configmap.yaml` et modifiez `APP_MESSAGE`, par exemple :

```yaml
APP_MESSAGE: "Mon message a changé"
```

Appliquez la modification et redémarrez les Pods pour que la nouvelle variable d’environnement soit lue :

```bash
kubectl apply -f manifests/10-configmap.yaml
kubectl -n kube-training rollout restart deployment/flask-app
kubectl -n kube-training rollout status deployment/flask-app
kubectl -n kube-training port-forward svc/flask-app 8080:80
```

Dans un autre terminal, vérifiez le nouveau message avec `curl http://localhost:8080/`. Arrêtez le `port-forward` avec `Ctrl+C`.

## Partie B — Secret applicatif

Créez un Secret de démonstration. N’utilisez aucune vraie clé :

```bash
kubectl -n kube-training create secret generic flask-app-secret \
  --from-literal=API_KEY='demo-not-a-real-secret' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n kube-training get secret flask-app-secret
```

Le Deployment référence déjà ce Secret de façon optionnelle. Redémarrez le Deployment puis vérifiez que les Pods sont prêts :

```bash
kubectl -n kube-training rollout restart deployment/flask-app
kubectl -n kube-training rollout status deployment/flask-app
kubectl -n kube-training get pods
```

Un Secret Kubernetes standard est encodé en base64 ; ce n’est pas automatiquement du chiffrement. Ne l’affichez pas avec `-o yaml` et ne le commitez jamais.

## Partie C — Comprendre requests et limits

Lisez la section `resources` dans `manifests/20-deployment.yaml` :

```yaml
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
```

Répondez avant de poursuivre :

- Que représente `100m` de CPU ? (Indice : 1000m = 1 CPU.)
- À quoi sert `requests` lors du placement du Pod ?
- Que peut-il se passer si un conteneur dépasse sa limite mémoire ?

Observez les ressources :

```bash
kubectl -n kube-training describe pod <nom-du-pod>
kubectl describe nodes
kubectl -n kube-training get events --sort-by=.lastTimestamp
```

Remplacez `<nom-du-pod>` par le nom réel d’un Pod.

### Mesurer la consommation réelle

Jusqu’ici vous avez lu des valeurs déclarées. Elles ne disent pas ce que
l’application consomme vraiment. L’API de métriques de Kubernetes n’est pas
installée par défaut : c’est `metrics-server` qui l’alimente, à partir des
kubelets.

Vérifiez d’abord la version de votre cluster : `metrics-server` 0.9 demande
Kubernetes 1.34 ou plus récent.

```bash
kubectl version
```

Si votre serveur est plus ancien, remplacez `v0.9.0` par `v0.8.1` dans la
commande suivante : la série 0.8 accepte Kubernetes 1.31 et au-delà.

Installez-le. La version est fixée volontairement : `latest` change avec le
temps et ne donnerait pas le même résultat à tout le monde.

```bash
MS=https://github.com/kubernetes-sigs/metrics-server
kubectl apply -f $MS/releases/download/v0.9.0/components.yaml
```

Sur Kind, une étape supplémentaire est nécessaire. Les kubelets présentent un
certificat auto-signé qui ne contient pas l’adresse IP du nœud : metrics-server
refuse donc de les interroger. Autorisez cette exception :

```bash
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment/metrics-server
```

`--kubelet-insecure-tls` désactive la vérification du certificat des kubelets.
La documentation de metrics-server le réserve explicitement aux environnements
de test. Ne le reproduisez pas sur un cluster de production : il faut y faire
signer les certificats des kubelets par l’autorité du cluster.

**Ne lancez cette commande qu’une fois.** Le `op: add` sur `args/-` ajoute un
élément à la fin de la liste : relancée, elle ajouterait une deuxième fois le
même argument. Contrôlez le résultat :

```bash
kubectl -n kube-system get deployment metrics-server -o yaml | grep -A 8 "args:"
```

`--kubelet-insecure-tls` doit apparaître une seule fois. S’il y figure en
double, ouvrez le déploiement et supprimez la ligne en trop :

```bash
kubectl -n kube-system edit deployment metrics-server
```

`kubectl edit` ouvre la ressource dans votre éditeur. À l’enregistrement, la
modification est envoyée à l’API et un nouveau Pod est créé.

Patientez une minute avant la suite. Le relevé a lieu toutes les 15 secondes et
il en faut deux pour que l’API réponde. Tant qu’elle n’est pas prête, la
commande suivante affiche `error: Metrics API not available` : c’est normal, ne
relancez pas l’installation.

Vérifiez que l’API est disponible, puis relevez les mesures :

```bash
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl -n kube-training top pods
```

La colonne `AVAILABLE` doit afficher `True`.

Comparez maintenant deux choses différentes :

```bash
kubectl describe node <nom-du-worker> | grep -A 6 "Allocated resources"
kubectl top node <nom-du-worker>
```

Remplacez `<nom-du-worker>` par le nom d’un nœud worker.

- `describe node` affiche les ressources **réservées**. Les pourcentages sont
  calculés à partir des `requests` des Pods placés sur le nœud, pas à partir de
  leur consommation.
- `top node` affiche la consommation **réelle**, mesurée.

Répondez :

- Que consomme réellement un Pod de l’application, comparé aux `requests: cpu:
  100m` déclarées ?
- Un nœud peut-il refuser un nouveau Pod alors que `top node` le montre
  largement inactif ? Pourquoi ?
- Si vous divisiez les `requests` par dix, l’application consommerait-elle moins
  de CPU ?

## Partie D — Observer le placement avec nodeSelector

Un `nodeSelector` demande à Kubernetes de placer un Pod sur un nœud qui possède un label précis. Nous allons utiliser un Deployment de test pour ne pas modifier l’application principale.

1. Choisissez un worker et ajoutez-lui un label :

```bash
kubectl get nodes
kubectl label node <nom-du-worker> tp04=ok
kubectl get nodes --show-labels
```

Remplacez `<nom-du-worker>` par le nom réel du worker.

2. Créez une copie du Deployment :

```bash
cp manifests/20-deployment.yaml /tmp/deployment-tp04.yaml
```

Dans `/tmp/deployment-tp04.yaml`, effectuez les modifications suivantes :

- `metadata.name` : `flask-app-tp04`
- `spec.replicas` : `1`
- `spec.selector.matchLabels.app.kubernetes.io/name` : `flask-app-tp04`
- `spec.template.metadata.labels.app.kubernetes.io/name` : `flask-app-tp04`
- Sous `spec.template.spec`, ajoutez :

```yaml
      nodeSelector:
        tp04: ok
```

Conservez l’image et `imagePullSecrets` du fichier d’origine. Si l’image GHCR est privée, le Deployment de test doit lui aussi référencer `ghcr-pull`.

3. Appliquez le Deployment de test et observez le nœud choisi :

```bash
kubectl apply -f /tmp/deployment-tp04.yaml
kubectl -n kube-training rollout status deployment/flask-app-tp04
kubectl -n kube-training get pods -l app.kubernetes.io/name=flask-app-tp04 -o wide
```

4. Dans le même fichier, remplacez `tp04: ok` par `tp04: absent`, puis appliquez la modification :

```bash
kubectl apply -f /tmp/deployment-tp04.yaml
kubectl -n kube-training get pods -l app.kubernetes.io/name=flask-app-tp04
kubectl -n kube-training get events --sort-by=.lastTimestamp
```

Le nouveau Pod reste normalement `Pending`, car aucun nœud ne porte le label demandé. L’application principale `flask-app` continue de fonctionner : vous avez modifié uniquement le Deployment de test.

5. Supprimez le Deployment de test et le label :

```bash
kubectl -n kube-training delete deployment flask-app-tp04
kubectl label node <nom-du-worker> tp04-
rm -f /tmp/deployment-tp04.yaml
```

## Partie E — Monter un volume emptyDir (facultatif)

Un volume `emptyDir` est un répertoire temporaire créé pour un Pod. Les conteneurs du même Pod peuvent le partager. Les données restent disponibles pendant la vie du Pod, mais elles sont perdues quand ce Pod est supprimé et remplacé.

1. Ouvrez `manifests/20-deployment.yaml`.
2. Dans le conteneur `flask-app`, ajoutez sous `ports:` ce montage :

```yaml
          volumeMounts:
            - name: donnees-temporaires
              mountPath: /tmp/formation
```

3. Dans `spec.template.spec`, au même niveau que `containers:`, ajoutez :

```yaml
      volumes:
        - name: donnees-temporaires
          emptyDir: {}
```

Conservez le champ `imagePullSecrets` ajouté au TP03. Respectez l’indentation YAML.

4. Appliquez le Deployment et attendez que les deux Pods soient prêts :

```bash
kubectl apply -f manifests/20-deployment.yaml
kubectl -n kube-training rollout status deployment/flask-app
kubectl -n kube-training get pods -l app.kubernetes.io/name=flask-app
```

La commande précédente affiche deux Pods. **Notez leurs deux noms par écrit** :
vous en aurez besoin jusqu’à la fin de la partie. Nous les appellerons ici
`<pod-A>` et `<pod-B>`.

5. Écrivez un fichier dans **chacun** des deux Pods. Le Deployment en compte
   deux : si vous n’écrivez que dans l’un, la suite ne prouvera rien.

```bash
kubectl -n kube-training exec <pod-A> -- sh -c 'echo bonjour > /tmp/formation/test.txt'
kubectl -n kube-training exec <pod-B> -- sh -c 'echo bonjour > /tmp/formation/test.txt'
```

Relisez-les pour vérifier que les deux contiennent bien le fichier :

```bash
kubectl -n kube-training exec <pod-A> -- cat /tmp/formation/test.txt
kubectl -n kube-training exec <pod-B> -- cat /tmp/formation/test.txt
```

Les deux doivent afficher `bonjour`.

6. Supprimez `<pod-A>`, et lui seul :

```bash
kubectl -n kube-training delete pod <pod-A>
kubectl -n kube-training rollout status deployment/flask-app
kubectl -n kube-training get pods -l app.kubernetes.io/name=flask-app
```

La liste montre `<pod-B>`, toujours là, et un Pod au nom nouveau créé par le
ReplicaSet pour remplacer `<pod-A>`. Notez ce nouveau nom, `<pod-C>`.

7. Relisez le fichier dans ces deux Pods :

```bash
kubectl -n kube-training exec <pod-B> -- ls -l /tmp/formation
kubectl -n kube-training exec <pod-C> -- ls -l /tmp/formation
```

`<pod-B>` contient toujours `test.txt`. `<pod-C>` affiche un répertoire vide :
il a reçu un volume `emptyDir` neuf.

Deux enseignements, et le second compte autant que le premier : un `emptyDir`
disparaît avec son Pod, et il n’est jamais partagé entre deux Pods, même issus
du même Deployment.

## Partie F — Mettre à jour l’application et revenir en arrière

Cette partie vous montre comment publier une nouvelle version, effectuer un rolling update et revenir à la version précédente.

1. Dans `app/app.py`, repérez la ligne qui contient `<title>` et remplacez-la :

```html
<title>Kubernetes Orchestration - Flask</title>
```

par :

```html
<title>Kubernetes Orchestration - Flask TP04-2</title>
```

Nous modifions le titre et non le message, car `APP_MESSAGE` est fourni par le ConfigMap et remplacerait toute valeur écrite dans le code.

2. Construisez et publiez une nouvelle image. Utilisez le même compte GHCR que dans le TP01. Le token du TP03 porte `read:packages` et ne suffit pas pour publier ; utilisez celui du TP01, avec `write:packages` :

```bash
read -p "Identifiant GitHub : " GHCR_USER
read -s -p "Token GHCR avec write:packages : " GHCR_TOKEN
echo
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
unset GHCR_TOKEN

export OWNER="$GHCR_USER"
export IMAGE="ghcr.io/$OWNER/kubernetes-orchestration"

docker build -t "$IMAGE:tp04-2" .
docker push "$IMAGE:tp04-2"
```

Vérifiez que le package reste privé. Le Secret `ghcr-pull` créé au TP03 doit toujours permettre de télécharger cette image.

3. Remplacez l’image du Deployment :

```bash
kubectl -n kube-training set image deployment/flask-app flask-app="$IMAGE:tp04-2"
kubectl -n kube-training rollout status deployment/flask-app
```

4. Observez les ReplicaSets et l’historique :

```bash
kubectl -n kube-training get replicasets
kubectl -n kube-training rollout history deployment/flask-app
```

Vous devez voir l’ancien ReplicaSet et le nouveau. Kubernetes remplace progressivement les Pods selon la stratégie de mise à jour du Deployment.

Ce Deployment ne déclare pas de stratégie : il utilise donc le défaut, `RollingUpdate`, avec au plus 25 % de Pods en surplus et 25 % indisponibles. Sur deux répliques, `maxSurge` est arrondi au-dessus et vaut 1, `maxUnavailable` est arrondi en dessous et vaut 0 : le remplacement se fait donc un Pod à la fois, en ajoutant le nouveau avant de retirer l'ancien. Ce calcul cadence le remplacement, il ne garantit pas pour autant l'absence de coupure : une requête en cours peut être perdue si l'application ne gère pas son arrêt, et un nouveau Pod n'absorbe du trafic qu'une fois `Ready`.

Vérifiez le nouveau titre avant le rollback :

```bash
kubectl -n kube-training port-forward svc/flask-app 8080:80
```

Dans un autre terminal :

```bash
curl -s http://127.0.0.1:8080/ | grep '<title>'
```

Le titre doit contenir `TP04-2`. Arrêtez le `port-forward` avec `Ctrl+C` avant de poursuivre.

5. Revenez à la version précédente :

```bash
kubectl -n kube-training rollout undo deployment/flask-app
kubectl -n kube-training rollout status deployment/flask-app
```

6. Vérifiez le titre après le rollback avec un `port-forward` :

```bash
kubectl -n kube-training port-forward svc/flask-app 8080:80
```

Dans un autre terminal :

```bash
curl -s http://127.0.0.1:8080/ | grep '<title>'
```

Avant le `rollout undo`, le titre contient `TP04-2`. Après le `rollout undo`, il ne le contient plus. Arrêtez le `port-forward` avec `Ctrl+C`. Si le port 8080 est déjà utilisé, choisissez un autre port local libre.

Nettoyez la session GHCR :

```bash
docker logout ghcr.io
unset OWNER IMAGE GHCR_USER
```

## À retenir

- Un ConfigMap sert à injecter de la configuration non sensible.
- Un Secret sert à stocker des données sensibles, mais doit être protégé par des droits et une configuration adaptés.
- Les requests influencent le placement ; les limits définissent des plafonds.
- Les requests sont une réservation, pas une mesure : l’ordonnanceur compte les requests, `kubectl top` montre la consommation réelle, et les deux peuvent être très éloignées.
- `nodeSelector` impose une contrainte simple sur les labels des nœuds.
- `emptyDir` est temporaire : sa durée de vie est celle du Pod, pas celle du conteneur. Il appartient à un seul Pod et n’est jamais partagé entre deux Pods d’un même Deployment.
- Un rolling update remplace progressivement les Pods, selon la stratégie du Deployment (`RollingUpdate` par défaut) ; `rollout undo` permet de revenir à la révision précédente.
- Un PVC sert à demander un stockage persistant ; il n’est pas créé dans cet exercice.

## Questions

1. Pourquoi faut-il redémarrer le Pod pour relire une variable d’environnement issue du ConfigMap ?
2. Quelle différence entre requests et limits ?
3. Un nœud affiche 80 % de CPU réservé dans `describe node` et 5 % de CPU utilisé dans `top node`. Comment expliquez-vous cet écart, et lequel des deux chiffres empêche le placement d’un nouveau Pod ?
4. Pourquoi le Pod reste-t-il Pending quand aucun nœud ne porte le label demandé ?
5. À quel moment les données d’un `emptyDir` sont-elles perdues ?
6. Quelle différence entre `emptyDir` et un stockage persistant demandé via PVC ?
7. Que se passe-t-il pendant un rolling update ?
8. Que fait exactement la commande `kubectl rollout undo` ?


---

**Suite :** [TP05 — Diagnostiquer une panne et vérifier les accès](TP05-administration-diagnostic-securite.md)
