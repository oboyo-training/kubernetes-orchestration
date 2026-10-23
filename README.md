# Kubernetes — Orchestration des conteneurs

Ce dépôt contient l’application fil rouge, les manifestes et les six TP de la formation. Suivez les TP dans l’ordre : chaque TP réutilise ce qui a été vu précédemment.

## Parcours

| TP | Sujet | À la fin du TP |
|---|---|---|
| [TP01](tp/TP01-application-conteneur.md) | Application, Docker et GHCR | Vous avez construit et publié l’image de l’application. |
| [TP02](tp/TP02-premiers-pas-kubernetes.md) | Premiers pas dans Kubernetes | Vous savez créer un Pod, un namespace et un Service, puis tester avec `port-forward`. |
| [TP03](tp/TP03-pod-deployment-service.md) | Déployer l’application | Vous avez déployé l’application et corrigé le problème d’accès à une image privée. |
| [TP04](tp/TP04-configuration-ressources-noeuds.md) | Configuration, ressources et mise à jour | Vous avez modifié un ConfigMap, observé requests/limits, mis à jour l’application par rolling update et annulé la mise à jour. |
| [TP05](tp/TP05-administration-diagnostic-securite.md) | Diagnostic et sécurité | Vous avez diagnostiqué un Service qui a des endpoints mais ne répond pas, et vérifié des droits RBAC. |
| [TP06](tp/TP06-gateway-api.md) | Gateway API | Vous avez exposé l’application en HTTP depuis votre poste. |

Les six énoncés sont aussi listés dans [l’index des TP](tp/README.md).

## Prérequis

L’environnement recommandé pour la formation est **Ubuntu sous WSL2 avec Docker Desktop et l’intégration WSL activée**.

Installez et vérifiez les outils suivants avant de commencer :

- [Git — installation](https://git-scm.com/downloads)
- [Docker — installation](https://docs.docker.com/get-started/get-docker/)
- [kubectl — installation](https://kubernetes.io/docs/tasks/tools/#kubectl)
- [Kind — installation](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [Helm 3 — installation](https://helm.sh/docs/intro/install/) (utilisé au TP06)
- [curl — téléchargement](https://curl.se/download.html)
- [Python 3.11 ou plus récent — téléchargement](https://www.python.org/downloads/) (TP01)

Vérifiez que les commandes suivantes fonctionnent :

```bash
git --version
docker version
kubectl version --client
kind version
helm version
curl --version
python3 --version
```

Docker doit pouvoir démarrer des conteneurs. Si `docker version` affiche une erreur de connexion au daemon, corrigez Docker avant de commencer.

## Votre copie du dépôt

Chaque participant travaille dans sa propre copie du dépôt. Vous pourrez ainsi modifier les manifestes, publier votre image et conserver votre travail après la formation.

1. Ouvrez https://github.com/oboyo-training/kubernetes-orchestration et cliquez sur **Fork**, en haut à droite. Conservez le nom proposé.
2. Clonez votre fork, et non le dépôt d’origine :

```bash
git clone https://github.com/VOTRE-IDENTIFIANT/kubernetes-orchestration.git
cd kubernetes-orchestration
```

3. Vérifiez que l’origine est bien la vôtre :

```bash
git remote -v
```

4. À chaque étape marquante d’un TP, enregistrez votre travail :

```bash
git add -A
git commit -m "TP03 - déploiement de l'application"
git push
```

Votre identifiant GitHub est aussi le propriétaire de vos images : au TP01 vous publierez dans `ghcr.io/VOTRE-IDENTIFIANT/kubernetes-orchestration`, et au TP03 vous remplacerez le champ `image:` du Deployment par cette adresse.

Pour récupérer une correction apportée au dépôt d’origine pendant la formation :

```bash
git remote add upstream https://github.com/oboyo-training/kubernetes-orchestration.git
git fetch upstream
git merge upstream/main
```

Facultatif : dans l’onglet Actions de votre fork, GitHub désactive les workflows par défaut. Si vous les activez, chaque push lancera les tests et la construction de l’image sur votre propre dépôt.

## Démarrer le cluster

Le TP02 vous guide dans la création du cluster. Depuis la racine du dépôt, la commande est :

```bash
kind create cluster --config kind/cluster.yaml --wait 120s
kubectl get nodes -o wide
```

Les trois nœuds doivent être `Ready`.

La configuration épingle l’image `kindest/node:v1.37.0`, pour que tout le monde
travaille sur la même version de Kubernetes. C’est ce qu’attendent
`metrics-server` 0.9, qui demande Kubernetes 1.34 ou plus récent, et NGINX
Gateway Fabric 2.7.2, qui demande 1.32 ou plus récent. Si la création du
cluster échoue en indiquant que l’image est inconnue, votre binaire `kind` est
trop ancien : mettez-le à jour.

## Organisation du dépôt

```text
app/                          application Flask
tests/                        tests de l’application
pytest.ini                    configuration des tests
kind/cluster.yaml             configuration du cluster Kind
manifests/                    manifestes utilisés pendant les TP
tp/                           énoncés des six TP
docs/installation-gateway.md  guide d’installation pour le TP06
.github/workflows/            tests et publication de l’image GHCR
bonus/                        exercices complémentaires
```

## Sécurité

- Ne mettez jamais de token GitHub ou de secret réel dans un fichier du dépôt.
- Au TP01, utilisez un token GHCR autorisé à publier une image.
- Au TP03, utilisez un token autorisé à lire le package privé (`read:packages`).
- Un Secret Kubernetes standard n’est pas automatiquement chiffré.
- Kind est un environnement de lab, pas un cluster de production.
- Au TP04, `--kubelet-insecure-tls` désactive une vérification de certificat. Ce réglage est réservé aux environnements de test comme Kind.

## Nettoyer le cluster

À la fin de la formation, supprimez le cluster si vous n’en avez plus besoin :

```bash
kind delete cluster --name kube-training
```

## TP bonus (facultatifs)

Après les six TP principaux, vous pouvez poursuivre avec :

- [Bonus — Déployer une application avec Flux](bonus/fluxcd/README.md)
- [Bonus — Utiliser Vault avec External Secrets Operator](bonus/vault-eso/README.md)

## Documentation officielle

- [Kubernetes](https://kubernetes.io/docs/home/)
- [Kubernetes — Concepts](https://kubernetes.io/docs/concepts/)
- [kubectl — Référence rapide](https://kubernetes.io/docs/reference/kubectl/quick-reference/)
- [Kind](https://kind.sigs.k8s.io/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [NGINX Gateway Fabric](https://docs.nginx.com/nginx-gateway-fabric/)
- [Flux](https://fluxcd.io/flux/)
- [External Secrets Operator](https://external-secrets.io/)
- [HashiCorp Vault](https://developer.hashicorp.com/vault/docs)
