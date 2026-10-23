# Bonus — Utiliser Vault avec External Secrets Operator

Ce TP est facultatif. Il montre comment récupérer une valeur stockée dans Vault et la rendre disponible à une application Kubernetes grâce à External Secrets Operator (ESO).

**Dans ce TP, nous utilisons ESO. Nous n’utilisons pas Vault Agent Injector.**

## Objectif

À la fin du TP, vous saurez expliquer le chemin suivant :

```text
Vault → External Secrets Operator → Secret Kubernetes → application
```

Vault conserve la valeur source. ESO la lit et crée un Secret Kubernetes. L’application consomme ce Secret comme les autres Secrets Kubernetes.

## Prérequis

- Les TP principaux sont terminés.
- Le cluster Kind fonctionne.
- Helm 3 et kubectl sont installés.
- Vous avez accès à Internet.
- Vous travaillez uniquement avec des valeurs de démonstration.

Vérifiez le cluster :

```bash
kubectl get nodes
helm version
```

## 1. Installer Vault dans le cluster de lab

Cette configuration est réservée à la formation : Vault démarre en mode développement, sans stockage durable ni sécurité adaptée à la production. N’y placez aucun secret réel.

Ajoutez le dépôt Helm HashiCorp et installez Vault :

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
helm install vault hashicorp/vault \
  --version 0.34.1 \
  --namespace vault --create-namespace \
  --set "server.dev.enabled=true" \
  --wait --timeout 5m
```

Vérifiez que le Pod démarre :

```bash
kubectl -n vault get pods
kubectl -n vault get svc
```

Ouvrez un shell dans le Pod Vault :

```bash
kubectl -n vault exec -it vault-0 -- sh
```

Dans ce shell, vérifiez Vault :

```bash
vault status
```

En mode développement, Vault est initialisé automatiquement. La configuration et le token de développement ne sont pas destinés à un environnement réel.

## 2. Créer une valeur de démonstration dans Vault

Toujours dans le shell du Pod Vault, activez un moteur KV version 2 et ajoutez une valeur fictive :

```bash
vault secrets list
vault kv put secret/kubernetes-demo API_KEY="demo-key-not-a-real-secret"
vault kv get secret/kubernetes-demo
```

Notez le chemin du secret : `secret/kubernetes-demo`. La clé à lire est `API_KEY`.

Sortez du shell :

```bash
exit
```

## 3. Installer External Secrets Operator

Installez ESO avec son dépôt Helm officiel :

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm show values external-secrets/external-secrets --version 0.20.1 | grep -n -A 3 "crds:"
helm install external-secrets external-secrets/external-secrets \
  --version 0.20.1 \
  --namespace external-secrets --create-namespace \
  --set crds.create=true \
  --wait --timeout 5m
```

Vérifiez que les Pods sont prêts et que les ressources sont disponibles :

```bash
kubectl -n external-secrets get pods
kubectl get crd | grep external-secrets
```

## 4. Préparer l’accès de ESO à Vault

Pour ce lab uniquement, nous allons utiliser le token de développement de Vault. Cette méthode simplifie la démonstration, mais **ne doit pas être utilisée en production**. En production, choisissez une méthode d’authentification adaptée et des permissions minimales.

Récupérez le token depuis la configuration du Pod Vault uniquement pour le lab :

```bash
kubectl -n vault exec vault-0 -- printenv VAULT_DEV_ROOT_TOKEN_ID
```

Copiez la valeur affichée dans une variable de shell. Ne l’écrivez pas dans un fichier :

```bash
read -s -p "Token Vault de développement : " VAULT_TOKEN
echo
```

Créez un Secret dans le namespace où ESO sera configuré :

```bash
kubectl -n kube-training create secret generic vault-token \
  --from-literal=token="$VAULT_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
unset VAULT_TOKEN
```

Cette forme reprend la même construction qu’au TP03 : elle fabrique le
manifeste puis l’applique, ce qui crée le Secret ou le met à jour. Vous pouvez
donc relancer la commande après une tentative interrompue.
```

Le token reste une donnée sensible même dans un lab. Ne l’affichez pas et ne le commitez pas.

## 5. Créer un SecretStore

Créez le fichier `/tmp/vault-secretstore.yaml` :

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: vault-store
  namespace: kube-training
spec:
  provider:
    vault:
      server: "http://vault.vault.svc:8200"
      path: "secret"
      version: "v2"
      auth:
        tokenSecretRef:
          name: vault-token
          key: token
```

Appliquez le manifeste :

```bash
kubectl apply -f /tmp/vault-secretstore.yaml
kubectl -n kube-training get secretstore vault-store
kubectl -n kube-training describe secretstore vault-store
```

Le SecretStore décrit comment ESO se connecte à Vault. Si l’état n’est pas prêt, vérifiez l’adresse du service Vault, le token et les logs d’ESO.

## 6. Créer un ExternalSecret

Créez le fichier `/tmp/vault-externalsecret.yaml` :

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: flask-api-key
  namespace: kube-training
spec:
  refreshInterval: 1m
  secretStoreRef:
    name: vault-store
    kind: SecretStore
  target:
    name: flask-api-key
    creationPolicy: Owner
  data:
    - secretKey: API_KEY
      remoteRef:
        key: kubernetes-demo
        property: API_KEY
```

Appliquez le manifeste et vérifiez l’état :

```bash
kubectl apply -f /tmp/vault-externalsecret.yaml
kubectl -n kube-training get externalsecret
kubectl -n kube-training describe externalsecret flask-api-key
kubectl -n kube-training get secret flask-api-key
```

Le Secret Kubernetes `flask-api-key` doit apparaître. Ne l’affichez pas avec `-o yaml` et ne lisez pas sa valeur dans le terminal.

Si le Secret n’est pas créé, consultez les événements et les logs du contrôleur :

```bash
kubectl -n kube-training get events --sort-by=.lastTimestamp
kubectl -n external-secrets logs deployment/external-secrets
```

## 7. Relier le Secret à l’application

Pour éviter de modifier le Deployment principal, créez une copie de test dans `/tmp/flask-api-key-test.yaml` à partir de `manifests/20-deployment.yaml`. Dans cette copie :

- changez le nom du Deployment en `flask-app-eso-test` ;
- changez le selector et le label de Pod en `app.kubernetes.io/name: flask-app-eso-test` ;
- conservez la même image et la configuration non sensible ;
- ajoutez cette variable dans le conteneur :

```yaml
env:
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: flask-api-key
        key: API_KEY
```

- retirez de cette copie l’ancien bloc `env` qui référence `flask-app-secret` ;
- gardez `imagePullSecrets` si votre image GHCR est privée.

Appliquez la copie, puis vérifiez le démarrage :

```bash
kubectl apply -f /tmp/flask-api-key-test.yaml
kubectl -n kube-training rollout status deployment/flask-app-eso-test
kubectl -n kube-training get pods -l app.kubernetes.io/name=flask-app-eso-test
```

L’application ne doit jamais afficher la valeur de la clé. Le but est de vérifier que le Secret existe et peut être référencé par un Pod, pas d’afficher son contenu.

## 8. Nettoyer les ressources du bonus

Supprimez d’abord les ressources de test :

```bash
kubectl delete -f /tmp/flask-api-key-test.yaml
kubectl delete -f /tmp/vault-externalsecret.yaml
kubectl delete -f /tmp/vault-secretstore.yaml
kubectl -n kube-training delete secret flask-api-key --ignore-not-found
kubectl -n kube-training delete secret vault-token --ignore-not-found
rm -f /tmp/flask-api-key-test.yaml /tmp/vault-externalsecret.yaml /tmp/vault-secretstore.yaml
```

Pour supprimer les installations de lab :

```bash
helm uninstall external-secrets -n external-secrets
helm uninstall vault -n vault
kubectl delete namespace external-secrets vault
```

## À retenir

- Vault conserve la valeur source.
- ESO récupère la valeur depuis Vault et crée un Secret Kubernetes.
- L’application lit le Secret via une référence Kubernetes standard.
- Ne stockez jamais un token ou une clé réelle dans Git.
- Le mode développement de Vault et le token root ne conviennent pas à la production.

## Documentation officielle

- [External Secrets Operator — documentation](https://external-secrets.io/)
- [HashiCorp Vault — documentation](https://developer.hashicorp.com/vault/docs)
- [Kubernetes — Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
