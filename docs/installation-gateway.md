# Guide d’installation — Gateway API dans Kind

Ce guide accompagne le TP06. Suivez les étapes dans l’ordre. Il utilise Kind, Gateway API et NGINX Gateway Fabric. MetalLB n’est pas nécessaire.

## 1. Vérifier le cluster Kind

Depuis la racine du dépôt :

```bash
kubectl get nodes
```

Les trois nœuds doivent être `Ready`. Aucun port fixe de votre poste n’est réservé par Kind. L’accès HTTP sera réalisé avec `kubectl port-forward` au TP06.

## 2. Installer les ressources Gateway API

Nous utilisons NGINX Gateway Fabric 2.7.2 pour ce lab. Installez les CRD Gateway API standard correspondant à cette version, soit Gateway API v1.6.1 :

```bash
kubectl kustomize "https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.7.2" | kubectl apply -f -
```

Cette commande installe le canal standard de Gateway API, soit onze définitions de ressources : Gateway API est une famille de types de routes, et HTTPRoute n'en est qu'un. Les TP n'utilisent que GatewayClass, Gateway et HTTPRoute. Le canal standard ne contient que ce qui est stabilisé ; le canal expérimental existe à part.

## 3. Installer NGINX Gateway Fabric avec Helm

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --version 2.7.2 \
  --create-namespace --namespace nginx-gateway \
  --wait --timeout 5m \
  --set nginx.service.type=NodePort \
  --set nginx.service.externalTrafficPolicy=Cluster \
  --set-json 'nginx.service.nodePorts=[{"port":30080,"listenerPort":80}]'
```

Attendez la fin de l’installation, puis vérifiez les Pods et les Services :

```bash
kubectl -n nginx-gateway get pods,svc
kubectl get gatewayclass
kubectl describe gatewayclass nginx
```

Les Pods du contrôleur doivent être `Running` et la GatewayClass `nginx` doit être acceptée. Le Service de données NGINX sera créé plus tard, lorsque vous appliquerez la Gateway au TP06.

## 4. Vérifier l’application

Avant de créer la Gateway, l’application doit fonctionner :

```bash
kubectl -n kube-training get pods,svc,endpoints
kubectl -n kube-training rollout status deployment/flask-app
```

Si les Pods ne sont pas prêts, revenez au TP03 et corrigez le problème avant de continuer.

## 5. Comprendre le chemin du trafic

Le chemin réseau de ce TP est :

```text
Votre poste : 127.0.0.1:8080
        |
        v
kubectl port-forward vers le Service de données NGINX
        |
        v
Service flask-gateway-nginx (namespace kube-training)
        |
        v
Gateway -> HTTPRoute -> Service flask-app:80 -> Pods Flask:5000
```

Le Service de données est créé dans le namespace de la Gateway, ici `kube-training`, lorsque la Gateway est attachée à la GatewayClass. Son nom est `flask-gateway-nginx`. Le Service est de type NodePort, qui serait un point d’entrée sur un vrai cluster. Dans ce lab, utilisez `port-forward` pour ne dépendre d’aucun port fixe de votre poste.

Après avoir créé la Gateway au TP06, vérifiez-le avec :

```bash
kubectl -n kube-training get svc flask-gateway-nginx
```

## 6. Si l’installation ne fonctionne pas

Vérifiez les éléments dans cet ordre :

```bash
helm list -n nginx-gateway
kubectl -n nginx-gateway get pods,svc
kubectl get gatewayclass
kubectl -n nginx-gateway get deployments
```

La dernière commande affiche le nom du Deployment du contrôleur. Reprenez-le
dans la commande suivante, à la place de `<nom-du-deployment>` :

```bash
kubectl -n nginx-gateway logs deployment/<nom-du-deployment> --tail=50
```

Le NodePort 30080 est configuré pour montrer ce que serait le point d’entrée du trafic sur un vrai cluster, mais les TP ne passent pas par lui : l’accès HTTP se fait en port-forward, ce qui évite de dépendre d’un port fixe de votre poste. S’il n’apparait pas, vous pouvez poursuivre.

## Version et limites du lab

Ce TP utilise les versions épinglées de Gateway API et NGINX Gateway Fabric indiquées ci-dessus. Si vous changez de version, vérifiez la compatibilité des CRD et des valeurs Helm.

Kind et NodePort servent à comprendre le routage HTTP dans un lab. Ce montage n’est pas un LoadBalancer cloud et ne configure ni IP publique, ni TLS de production, ni haute disponibilité.
