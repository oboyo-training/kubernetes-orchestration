# TP02 — Premiers pas dans Kubernetes

## Objectif

Créer un namespace, lancer un Pod avec une image publique, l’identifier avec des labels, puis y accéder à travers un Service et `port-forward`. Dans ce TP, nous créons les objets un par un : pas encore de Deployment.

## Prérequis

- TP01 terminé.
- Docker fonctionne sur votre poste.
- Kind et `kubectl` sont installés et répondent.

## 1. Vérifier le cluster

Si le cluster n’existe pas, créez-le depuis la racine du dépôt :

```bash
kind create cluster --config kind/cluster.yaml --wait 120s
kubectl get nodes
kubectl cluster-info
```

Les trois nœuds doivent être `Ready`.

## 2. Créer un namespace

Un namespace permet de regrouper des ressources Kubernetes.

```bash
kubectl create namespace tp02
kubectl get namespaces
kubectl get pods -n tp02
```

## 3. Créer un Pod NGINX

Créez le Pod directement avec kubectl :

```bash
kubectl run web --image=nginx:stable --labels="app=web" -n tp02
kubectl get pods -n tp02 -o wide
kubectl describe pod web -n tp02
kubectl get pod web -n tp02 --show-labels
```

Attendez que le Pod soit `Running` :

```bash
kubectl wait --for=condition=Ready pod/web -n tp02 --timeout=120s
```

## 4. Ajouter un second Pod avec BusyBox

BusyBox est une petite image qui contient notamment un shell et des commandes Linux.

```bash
kubectl run outil --image=busybox:1.36 -n tp02 -- sleep 3600
kubectl get pods -n tp02
kubectl wait --for=condition=Ready pod/outil -n tp02 --timeout=120s
kubectl exec -it outil -n tp02 -- sh
```

Dans le shell BusyBox, exécutez `ls`, puis tapez `exit` pour en sortir.

## 5. Créer un Service pour NGINX

Un Service fournit un point d’accès stable vers les Pods qui correspondent à son selector. Créez le Service avec cette commande :

```bash
kubectl expose pod web --name=web-svc --port=80 --target-port=80 -n tp02
kubectl get svc -n tp02
kubectl describe svc web-svc -n tp02
kubectl get endpoints web-svc -n tp02
```

Comparez le selector du Service avec le label du Pod :

```bash
kubectl get pod web -n tp02 --show-labels
kubectl get svc web-svc -n tp02 -o yaml
```

Les labels doivent correspondre pour que le Service trouve le Pod.

Kubernetes tient aussi une seconde représentation de ces adresses, plus récente
et plus riche, les EndpointSlice :

```bash
kubectl get endpointslices -n tp02
```

Les deux coexistent et décrivent les mêmes adresses. `Endpoints` est l’API
d’origine : elle est dépréciée depuis Kubernetes 1.33 mais reste pleinement
prise en charge et ne sera pas supprimée ; nous la lisons dans ces TP parce que
sa sortie tient sur une ligne. `EndpointSlice`, stable depuis Kubernetes 1.21,
est celle que le cluster alimente en premier et que vous rencontrerez en
production : elle découpe les adresses en tranches et porte des informations
que l’objet `Endpoints` ne sait pas représenter.

## 6. Accéder au Service depuis votre poste

Dans un terminal, lancez :

```bash
kubectl port-forward -n tp02 svc/web-svc 8080:80
```

Laissez ce terminal ouvert. Dans un second terminal :

```bash
curl -I http://localhost:8080
```

Vous devez recevoir une réponse HTTP de NGINX. Arrêtez le `port-forward` avec `Ctrl+C`.

## 7. Observer les labels et les selectors

Affichez les Pods avec leur label :

```bash
kubectl get pods -n tp02 --show-labels
kubectl get pods -n tp02 -l app=web
```

Le sélecteur `app=web` retrouve le Pod NGINX, mais pas le Pod BusyBox.

Modifiez temporairement le selector du Service pour qu’il ne corresponde plus au Pod :

```bash
kubectl patch svc web-svc -n tp02 -p '{"spec":{"selector":{"app":"inexistant"}}}'
kubectl get endpoints web-svc -n tp02
```

Les endpoints sont vides : le Service ne trouve plus de Pod correspondant. Rétablissez le selector :

```bash
kubectl patch svc web-svc -n tp02 -p '{"spec":{"selector":{"app":"web"}}}'
kubectl get endpoints web-svc -n tp02
```

Les endpoints réapparaissent. Vous venez d’observer et de corriger une panne de selector. Au TP05, vous diagnostiquerez un autre problème de Service.

## 8. Nettoyer les ressources du TP

```bash
kubectl delete namespace tp02
```

La suppression du namespace supprime les ressources qu’il contient.

## À retenir

- Un Pod exécute un ou plusieurs conteneurs.
- Un namespace regroupe des ressources.
- Les labels identifient des ressources ; les selectors permettent de les retrouver.
- Un Service sélectionne les Pods par leurs labels.
- `port-forward` ouvre un accès temporaire depuis votre poste ; ce n’est pas une exposition de production.
- `Endpoints` et `EndpointSlice` décrivent les mêmes adresses : la première est l’API d’origine, la seconde celle que Kubernetes utilise aujourd’hui.

## Questions

1. Quelle différence entre un Pod et un conteneur ?
2. À quoi sert le namespace `tp02` ?
3. Comment le Service `web-svc` trouve-t-il le Pod NGINX ?
4. Que se passe-t-il si aucun Pod ne correspond au selector du Service ?
5. Pourquoi utilise-t-on `port-forward` dans ce TP ?


---

**Suite :** [TP03 — Déployer notre application sur Kubernetes](TP03-pod-deployment-service.md)
