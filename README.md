# GitOps on Kubernetes with Argo CD: Staging → Production

A complete GitOps delivery setup for an **on-prem Kubernetes cluster**: **Argo CD** (app-of-apps), **Kustomize** environments, a CI pipeline that builds and scans images, and **promotion to production through pull requests**. Git is the single source of truth. CI never runs `kubectl` against the cluster.

## Delivery flow

```
 developer ─► PR ─► merge to main
                       │
                 GitHub Actions (ci.yaml)
                 test ─► build ─► push to GHCR ─► Trivy scan
                       │
                       └─► commit: staging newTag = sha-abc1234
                                       │
            Argo CD watches Git ◄──────┘
            demo-api-staging: auto-sync, prune, self-heal ─► namespace demo-staging
                       │
          "promote-to-prod" workflow ─► PR: prod newTag = sha-abc1234
                       │  (review + checklist = approval gate)
                       ▼
            demo-api-prod syncs inside the prod sync window ─► namespace demo-prod
```

## Repository layout

```
argocd/
  project.yaml               AppProject: allowed repo + namespaces, prod sync window (Sun-Thu)
  root-app.yaml              app-of-apps, the only manifest applied by hand
  apps/
    demo-api-staging.yaml    auto-sync, prune, self-heal, retry with backoff
    demo-api-prod.yaml       same + notifications, ignores replicas (HPA owns them)
apps/demo-api/
  base/                      Deployment, Service, ConfigMap, Ingress, HPA, PDB
  overlays/staging/          namespace, image tag, host, debug logging
  overlays/prod/             namespace, image tag, host, more replicas/resources, stricter PDB & spread
src/                         the service (Flask + Prometheus metrics), Dockerfile, tests
.github/workflows/
  ci.yaml                    test → build → push → scan → bump staging tag
  promote.yaml               opens the staging → prod promotion PR
```

## Production-readiness built into the base

- **Zero-downtime rollouts:** `maxUnavailable: 0`, readiness and startup probes, `preStop` delay so traffic drains before the pod stops.
- **Resilience:** pods spread across nodes with `topologySpreadConstraints`, a **PodDisruptionBudget** for node drains and upgrades, and an **HPA** with scale-down stabilization.
- **Security:** non-root user, read-only root filesystem, all capabilities dropped, seccomp `RuntimeDefault`, image scanning in CI.
- **Drift control:** Argo CD `selfHeal` reverts manual `kubectl edit` changes, and `prune` removes resources deleted from Git.
- **Guardrails:** an AppProject restricts the source repo and target namespaces, and a **sync window** limits automatic prod changes to working hours. Manual sync is still allowed for emergencies.

## Bootstrap

```bash
# 1. install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. hand Argo CD the app-of-apps, everything else is pulled from Git
kubectl apply -n argocd -f argocd/project.yaml -f argocd/root-app.yaml
```

## Day-2 operations

| Task | How |
|---|---|
| Deploy a new version | Merge to `main`. Staging updates automatically. |
| Promote to prod | Actions → **promote-to-prod** → review and merge the PR |
| Roll back | `git revert` the promotion commit (preferred), or `argocd app rollback demo-api-prod <id>` in an emergency |
| See what's deployed | `argocd app get demo-api-prod`, or the image tag in `overlays/prod/kustomization.yaml` |
| Preview a change | `kustomize build apps/demo-api/overlays/prod \| kubectl diff -f -` |

## Tech
Kubernetes · Argo CD · Kustomize · GitHub Actions · GHCR · Trivy · Docker · ingress-nginx · Python
