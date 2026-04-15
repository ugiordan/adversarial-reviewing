# rhods-operator

**Repository:** opendatahub-io/rhods-operator  
**Analyzer Version:** 0.2.0  
**Extracted:** 2026-04-10T22:17:26Z  

---

## APIs Exposed

### CRDs

| Group | Version | Kind | Scope | Fields | Validation Rules | Source |
|-------|---------|------|-------|--------|------------------|--------|
| components.platform.opendatahub.io | v1alpha1 | Dashboard | Cluster | 22 | 1 | `config/crd/bases/components.platform.opendatahub.io_dashboards.yaml` |
| components.platform.opendatahub.io | v1alpha1 | DataSciencePipelines | Cluster | 27 | 1 | `config/crd/bases/components.platform.opendatahub.io_datasciencepipelines.yaml` |
| components.platform.opendatahub.io | v1alpha1 | FeastOperator | Cluster | 25 | 1 | `config/crd/bases/components.platform.opendatahub.io_feastoperators.yaml` |
| components.platform.opendatahub.io | v1alpha1 | Kserve | Cluster | 39 | 1 | `config/crd/bases/components.platform.opendatahub.io_kserves.yaml` |
| components.platform.opendatahub.io | v1alpha1 | Kueue | Cluster | 28 | 1 | `config/crd/bases/components.platform.opendatahub.io_kueues.yaml` |
| components.platform.opendatahub.io | v1alpha1 | LlamaStackOperator | Cluster | 25 | 1 | `config/crd/bases/components.platform.opendatahub.io_llamastackoperators.yaml` |
| components.platform.opendatahub.io | v1alpha1 | ModelController | Cluster | 27 | 1 | `config/crd/bases/components.platform.opendatahub.io_modelcontrollers.yaml` |
| components.platform.opendatahub.io | v1alpha1 | ModelRegistry | Cluster | 27 | 1 | `config/crd/bases/components.platform.opendatahub.io_modelregistries.yaml` |
| components.platform.opendatahub.io | v1alpha1 | Ray | Cluster | 25 | 1 | `config/crd/bases/components.platform.opendatahub.io_rays.yaml` |
| components.platform.opendatahub.io | v1alpha1 | TrainingOperator | Cluster | 25 | 1 | `config/crd/bases/components.platform.opendatahub.io_trainingoperators.yaml` |
| components.platform.opendatahub.io | v1alpha1 | TrustyAI | Cluster | 29 | 1 | `config/crd/bases/components.platform.opendatahub.io_trustyais.yaml` |
| components.platform.opendatahub.io | v1alpha1 | Workbenches | Cluster | 27 | 2 | `config/crd/bases/components.platform.opendatahub.io_workbenches.yaml` |
| datasciencecluster.opendatahub.io | v1 | DataScienceCluster | Cluster | 223 | 2 | `config/crd/bases/datasciencecluster.opendatahub.io_datascienceclusters.yaml` |
| datasciencecluster.opendatahub.io | v2 | DataScienceCluster | Cluster | 197 | 2 | `config/crd/bases/datasciencecluster.opendatahub.io_datascienceclusters.yaml` |
| dscinitialization.opendatahub.io | v1 | DSCInitialization | Cluster | 72 | 10 | `config/crd/bases/dscinitialization.opendatahub.io_dscinitializations.yaml` |
| dscinitialization.opendatahub.io | v2 | DSCInitialization | Cluster | 72 | 10 | `config/crd/bases/dscinitialization.opendatahub.io_dscinitializations.yaml` |
| features.opendatahub.io | v1 | FeatureTracker | Cluster | 19 | 0 | `config/crd/bases/features.opendatahub.io_featuretrackers.yaml` |
| infrastructure.opendatahub.io | v1 | HardwareProfile | Namespaced | 25 | 2 | `config/crd/bases/infrastructure.opendatahub.io_hardwareprofiles.yaml` |
| infrastructure.opendatahub.io | v1alpha1 | HardwareProfile | Namespaced | 25 | 2 | `config/crd/bases/infrastructure.opendatahub.io_hardwareprofiles.yaml` |
| services.platform.opendatahub.io | v1alpha1 | Auth | Cluster | 18 | 4 | `config/crd/bases/services.platform.opendatahub.io_auths.yaml` |
| services.platform.opendatahub.io | v1alpha1 | GatewayConfig | Cluster | 27 | 1 | `config/crd/bases/services.platform.opendatahub.io_gatewayconfigs.yaml` |
| services.platform.opendatahub.io | v1alpha1 | Monitoring | Cluster | 43 | 10 | `config/crd/bases/services.platform.opendatahub.io_monitorings.yaml` |

### Webhooks

| Name | Type | Path | Failure Policy | Service | Source |
|------|------|------|----------------|---------|--------|
| datasciencecluster-v1-defaulter.opendatahub.io | mutating | /mutate-datasciencecluster-v1 | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| datasciencecluster-v2-defaulter.opendatahub.io | mutating | /mutate-datasciencecluster-v2 | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| hardwareprofile-isvc-injector.opendatahub.io | mutating | /mutate-hardware-profile | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| hardwareprofile-llmisvc-injector.opendatahub.io | mutating | /mutate-hardware-profile | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| hardwareprofile-notebook-injector.opendatahub.io | mutating | /mutate-hardware-profile | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| connection-notebook.opendatahub.io | mutating | /platform-connection-notebook | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| connection-isvc.opendatahub.io | mutating | /platform-connection-isvc | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| connection-llmisvc.opendatahub.io | mutating | /platform-connection-llmisvc | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| dashboard-acceleratorprofile-validator.opendatahub.io | validating | /validate-dashboard-acceleratorprofile | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| dashboard-hardwareprofile-validator.opendatahub.io | validating | /validate-dashboard-hardwareprofile | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| datasciencecluster-v1-validator.opendatahub.io | validating | /validate-datasciencecluster-v1 | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| datasciencecluster-v2-validator.opendatahub.io | validating | /validate-datasciencecluster-v2 | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| dscinitialization-v1-validator.opendatahub.io | validating | /validate-dscinitialization-v1 | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| dscinitialization-v2-validator.opendatahub.io | validating | /validate-dscinitialization-v2 | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| kserve-isvc-kueuelabels-validator.opendatahub.io | validating | /validate-kueue | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| kserve-llmisvc-kueuelabels-validator.opendatahub.io | validating | /validate-kueue | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| kubeflow-kueuelabels-validator.opendatahub.io | validating | /validate-kueue | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| ray-kueuelabels-validator.opendatahub.io | validating | /validate-kueue | Fail | system/webhook-service | `config/webhook/manifests.yaml` |
| mdeployment.kb.io | mutating |  |  |  | `opt/manifests/kueue/rhoai/mutating_webhook_patch.yaml` |
| mpod.kb.io | mutating |  |  |  | `opt/manifests/kueue/rhoai/mutating_webhook_patch.yaml` |
| mjob.kb.io | mutating |  |  |  | `opt/manifests/kueue/rhoai/mutating_webhook_patch.yaml` |
| mdeployment.kb.io | mutating |  |  |  | `prefetched-manifests/kueue/rhoai/mutating_webhook_patch.yaml` |
| mpod.kb.io | mutating |  |  |  | `prefetched-manifests/kueue/rhoai/mutating_webhook_patch.yaml` |
| mjob.kb.io | mutating |  |  |  | `prefetched-manifests/kueue/rhoai/mutating_webhook_patch.yaml` |
| vdeployment.kb.io | validating |  |  |  | `opt/manifests/kueue/rhoai/validating_webhook_patch.yaml` |
| vpod.kb.io | validating |  |  |  | `opt/manifests/kueue/rhoai/validating_webhook_patch.yaml` |
| vjob.kb.io | validating |  |  |  | `opt/manifests/kueue/rhoai/validating_webhook_patch.yaml` |
| vdeployment.kb.io | validating |  |  |  | `prefetched-manifests/kueue/rhoai/validating_webhook_patch.yaml` |
| vpod.kb.io | validating |  |  |  | `prefetched-manifests/kueue/rhoai/validating_webhook_patch.yaml` |
| vjob.kb.io | validating |  |  |  | `prefetched-manifests/kueue/rhoai/validating_webhook_patch.yaml` |

## Dependencies

### Key External Dependencies

| Module | Version |
|--------|---------|
| github.com/go-logr/logr | v1.4.2 |
| github.com/operator-framework/api | v0.31.0 |
| github.com/prometheus-operator/prometheus-operator/pkg/apis/monitoring | v0.68.0 |
| github.com/prometheus/client_golang | v1.20.5 |
| k8s.io/api | v0.32.4 |
| k8s.io/apiextensions-apiserver | v0.32.4 |
| k8s.io/apimachinery | v0.32.4 |
| k8s.io/client-go | v0.32.4 |
| sigs.k8s.io/controller-runtime | v0.20.4 |

## Network Architecture

### Services

| Name | Type | Ports | Source |
|------|------|-------|--------|
| webhook-service | ClusterIP | 443/TCP | `config/webhook/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `opt/manifests/codeflare/webhook/service.yaml` |
| odh-dashboard | ClusterIP | 8443/TCP | `opt/manifests/dashboard/core-bases/base/service.yaml` |
| kserve-controller-manager-service | ClusterIP | 8443/TCP | `opt/manifests/kserve/manager/service.yaml` |
| kserve-webhook-server-service | ClusterIP | 443/TCP | `opt/manifests/kserve/webhook/service.yaml` |
| visibility-server | ClusterIP | 443/TCP | `opt/manifests/kueue/components/visibility/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `opt/manifests/kueue/components/webhook/service.yaml` |
| odh-model-controller-webhook-service | ClusterIP | 443/TCP | `opt/manifests/modelcontroller/webhook/service.yaml` |
| modelmesh-controller | ClusterIP | 8080/TCP | `opt/manifests/modelmeshserving/overlays/odh/manager/service.yaml` |
| modelmesh-webhook-server-service | ClusterIP | 9443/TCP | `opt/manifests/modelmeshserving/webhook/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `opt/manifests/modelregistry/webhook/service.yaml` |
| kuberay-operator | ClusterIP | 8080/TCP | `opt/manifests/ray/manager/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `opt/manifests/ray/webhook/service.yaml` |
| training-operator | ClusterIP | 8080/TCP, 443/TCP | `opt/manifests/trainingoperator/base/service.yaml` |
| service | ClusterIP | 443/TCP | `opt/manifests/workbenches/kf-notebook-controller/manager/service.yaml` |
| service | ClusterIP | 8080/TCP | `opt/manifests/workbenches/odh-notebook-controller/manager/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `opt/manifests/workbenches/odh-notebook-controller/webhook/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `prefetched-manifests/codeflare/webhook/service.yaml` |
| odh-dashboard | ClusterIP | 8443/TCP | `prefetched-manifests/dashboard/core-bases/base/service.yaml` |
| kserve-controller-manager-service | ClusterIP | 8443/TCP | `prefetched-manifests/kserve/manager/service.yaml` |
| kserve-webhook-server-service | ClusterIP | 443/TCP | `prefetched-manifests/kserve/webhook/service.yaml` |
| visibility-server | ClusterIP | 443/TCP | `prefetched-manifests/kueue/components/visibility/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `prefetched-manifests/kueue/components/webhook/service.yaml` |
| odh-model-controller-webhook-service | ClusterIP | 443/TCP | `prefetched-manifests/modelcontroller/webhook/service.yaml` |
| modelmesh-controller | ClusterIP | 8080/TCP | `prefetched-manifests/modelmeshserving/overlays/odh/manager/service.yaml` |
| modelmesh-webhook-server-service | ClusterIP | 9443/TCP | `prefetched-manifests/modelmeshserving/webhook/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `prefetched-manifests/modelregistry/webhook/service.yaml` |
| kuberay-operator | ClusterIP | 8080/TCP | `prefetched-manifests/ray/manager/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `prefetched-manifests/ray/webhook/service.yaml` |
| training-operator | ClusterIP | 8080/TCP, 443/TCP | `prefetched-manifests/trainingoperator/base/service.yaml` |
| service | ClusterIP | 443/TCP | `prefetched-manifests/workbenches/kf-notebook-controller/manager/service.yaml` |
| service | ClusterIP | 8080/TCP | `prefetched-manifests/workbenches/odh-notebook-controller/manager/service.yaml` |
| webhook-service | ClusterIP | 443/TCP | `prefetched-manifests/workbenches/odh-notebook-controller/webhook/service.yaml` |

### Ingress / Routing

| Kind | Name | Hosts | Paths | TLS | Source |
|------|------|-------|-------|-----|--------|
| Route | opendatahub-odh-gateway | opendatahub.apps-crc.testing |  | yes | `opt/manifests/workbenches/kf-notebook-controller/overlays/standalone-service-mesh/gateway-route.yaml` |
| Gateway | odh-gateway |  |  | no | `opt/manifests/workbenches/kf-notebook-controller/overlays/standalone-service-mesh/gateway.yaml` |
| Route | opendatahub-odh-gateway | opendatahub.apps-crc.testing |  | yes | `prefetched-manifests/workbenches/kf-notebook-controller/overlays/standalone-service-mesh/gateway-route.yaml` |
| Gateway | odh-gateway |  |  | no | `prefetched-manifests/workbenches/kf-notebook-controller/overlays/standalone-service-mesh/gateway.yaml` |
| DestinationRule | odh-tls-rule |  |  | no | `internal/controller/services/gateway/resources/destinationrule-tls.yaml` |
| Gateway | kserve-ingress-gateway |  |  | no | `opt/manifests/kserve/overlays/test/gateway/ingress_gateway.yaml` |
| Ingress | rayclient-ingress | localhost | / | no | `opt/manifests/ray/samples/ingress-rayclient-tls.yaml` |
| Gateway | kserve-ingress-gateway |  |  | no | `prefetched-manifests/kserve/overlays/test/gateway/ingress_gateway.yaml` |
| Ingress | rayclient-ingress | localhost | / | no | `prefetched-manifests/ray/samples/ingress-rayclient-tls.yaml` |
| Route | odh-dashboard |  |  | yes | `opt/manifests/dashboard/core-bases/base/routes.yaml` |
| Route | odh-dashboard |  |  | yes | `prefetched-manifests/dashboard/core-bases/base/routes.yaml` |

### Network Policies

| Name | Policy Types | Source |
|------|-------------|--------|
| odh-dashboard-allow-ports | Ingress | `opt/manifests/dashboard/modular-architecture/networkpolicy.yaml` |
| etcd | Ingress | `opt/manifests/modelmeshserving/overlays/odh/rbac/networkpolicy_etcd.yaml` |
| modelmesh-controller | Ingress | `opt/manifests/modelmeshserving/rbac/common/networkpolicy-controller.yaml` |
| modelmesh-runtimes | Ingress | `opt/manifests/modelmeshserving/rbac/common/networkpolicy-runtimes.yaml` |
| modelmesh-webhook | Ingress | `opt/manifests/modelmeshserving/rbac/common/networkpolicy-webhook.yaml` |
| odh-dashboard-allow-ports | Ingress | `prefetched-manifests/dashboard/modular-architecture/networkpolicy.yaml` |
| etcd | Ingress | `prefetched-manifests/modelmeshserving/overlays/odh/rbac/networkpolicy_etcd.yaml` |
| modelmesh-controller | Ingress | `prefetched-manifests/modelmeshserving/rbac/common/networkpolicy-controller.yaml` |
| modelmesh-runtimes | Ingress | `prefetched-manifests/modelmeshserving/rbac/common/networkpolicy-runtimes.yaml` |
| modelmesh-webhook | Ingress | `prefetched-manifests/modelmeshserving/rbac/common/networkpolicy-webhook.yaml` |
| kserve-controller-manager |  | `opt/manifests/kserve/overlays/odh/network-policies.yaml` |
| kserve-controller-manager |  | `prefetched-manifests/kserve/overlays/odh/network-policies.yaml` |

## Security

### Cluster Roles

| Name | Resources | Verbs | Source |
|------|-----------|-------|--------|
| redhat-ods-operator-metrics-reader |  | get | `config/rbac/auth_proxy_client_clusterrole.yaml` |
| dashboard-editor-role | dashboards | create, delete, get, list, patch, update, watch | `config/rbac/components_dashboard_editor_role.yaml` |
| dashboard-editor-role | dashboards/status | get | `config/rbac/components_dashboard_editor_role.yaml` |
| dashboard-viewer-role | dashboards | get, list, watch | `config/rbac/components_dashboard_viewer_role.yaml` |
| dashboard-viewer-role | dashboards/status | get | `config/rbac/components_dashboard_viewer_role.yaml` |
| datasciencepipelines-editor-role | datasciencepipelines | create, delete, get, list, patch, update, watch | `config/rbac/components_datasciencepipelines_editor_role.yaml` |
| datasciencepipelines-editor-role | datasciencepipelines/status | get | `config/rbac/components_datasciencepipelines_editor_role.yaml` |
| datasciencepipelines-viewer-role | datasciencepipelines | get, list, watch | `config/rbac/components_datasciencepipelines_viewer_role.yaml` |
| datasciencepipelines-viewer-role | datasciencepipelines/status | get | `config/rbac/components_datasciencepipelines_viewer_role.yaml` |
| kserve-editor-role | kserves | create, delete, get, list, patch, update, watch | `config/rbac/components_kserve_editor_role.yaml` |
| kserve-editor-role | kserves/status | get | `config/rbac/components_kserve_editor_role.yaml` |
| kserve-viewer-role | kserves | get, list, watch | `config/rbac/components_kserve_viewer_role.yaml` |
| kserve-viewer-role | kserves/status | get | `config/rbac/components_kserve_viewer_role.yaml` |
| kueue-editor-role | kueues | create, delete, get, list, patch, update, watch | `config/rbac/components_kueue_editor_role.yaml` |
| kueue-editor-role | kueues/status | get | `config/rbac/components_kueue_editor_role.yaml` |
| kueue-viewer-role | kueues | get, list, watch | `config/rbac/components_kueue_viewer_role.yaml` |
| kueue-viewer-role | kueues/status | get | `config/rbac/components_kueue_viewer_role.yaml` |
| modelregistry-editor-role | modelregistries | create, delete, get, list, patch, update, watch | `config/rbac/components_modelregistry_editor_role.yaml` |
| modelregistry-editor-role | modelregistries/status | get | `config/rbac/components_modelregistry_editor_role.yaml` |
| modelregistry-viewer-role | modelregistries | get, list, watch | `config/rbac/components_modelregistry_viewer_role.yaml` |
| modelregistry-viewer-role | modelregistries/status | get | `config/rbac/components_modelregistry_viewer_role.yaml` |
| ray-editor-role | rays | create, delete, get, list, patch, update, watch | `config/rbac/components_ray_editor_role.yaml` |
| ray-editor-role | rays/status | get | `config/rbac/components_ray_editor_role.yaml` |
| ray-viewer-role | rays | get, list, watch | `config/rbac/components_ray_viewer_role.yaml` |
| ray-viewer-role | rays/status | get | `config/rbac/components_ray_viewer_role.yaml` |
| trainingoperator-editor-role | trainingoperators | create, delete, get, list, patch, update, watch | `config/rbac/components_trainingoperator_editor_role.yaml` |
| trainingoperator-editor-role | trainingoperators/status | get | `config/rbac/components_trainingoperator_editor_role.yaml` |
| trainingoperator-viewer-role | trainingoperators | get, list, watch | `config/rbac/components_trainingoperator_viewer_role.yaml` |
| trainingoperator-viewer-role | trainingoperators/status | get | `config/rbac/components_trainingoperator_viewer_role.yaml` |
| trustyai-editor-role | trustyais | create, delete, get, list, patch, update, watch | `config/rbac/components_trustyai_editor_role.yaml` |
| trustyai-editor-role | trustyais/status | get | `config/rbac/components_trustyai_editor_role.yaml` |
| trustyai-viewer-role | trustyais | get, list, watch | `config/rbac/components_trustyai_viewer_role.yaml` |
| trustyai-viewer-role | trustyais/status | get | `config/rbac/components_trustyai_viewer_role.yaml` |
| workbenches-editor-role | workbenches | create, delete, get, list, patch, update, watch | `config/rbac/components_workbenches_editor_role.yaml` |
| workbenches-editor-role | workbenches/status | get | `config/rbac/components_workbenches_editor_role.yaml` |
| workbenches-viewer-role | workbenches | get, list, watch | `config/rbac/components_workbenches_viewer_role.yaml` |
| workbenches-viewer-role | workbenches/status | get | `config/rbac/components_workbenches_viewer_role.yaml` |
| datasciencecluster-editor-role | datascienceclusters | create, delete, get, list, patch, update, watch | `config/rbac/datasciencecluster_datasciencecluster_editor_role.yaml` |
| datasciencecluster-editor-role | datascienceclusters/status | get | `config/rbac/datasciencecluster_datasciencecluster_editor_role.yaml` |
| datasciencecluster-viewer-role | datascienceclusters | get, list, watch | `config/rbac/datasciencecluster_datasciencecluster_viewer_role.yaml` |
| datasciencecluster-viewer-role | datascienceclusters/status | get | `config/rbac/datasciencecluster_datasciencecluster_viewer_role.yaml` |
| dscinitialization-editor-role | dscinitializations | create, delete, get, list, patch, update, watch | `config/rbac/dscinitialization_dscinitialization_editor_role.yaml` |
| dscinitialization-editor-role | dscinitializations/status | get | `config/rbac/dscinitialization_dscinitialization_editor_role.yaml` |
| dscinitialization-viewer-role | dscinitializations | get, list, watch | `config/rbac/dscinitialization_dscinitialization_viewer_role.yaml` |
| dscinitialization-viewer-role | dscinitializations/status | get | `config/rbac/dscinitialization_dscinitialization_viewer_role.yaml` |
| rhods-operator-role | clusterversions, nodes, rhmis | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | configmaps, events, namespaces, secrets, secrets/finalizers, serviceaccounts, services/finalizers | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | configmaps/status | delete, get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | deployments, persistentvolumeclaims, persistentvolumes, pods, pods/exec, pods/log | * | `config/rbac/role.yaml` |
| rhods-operator-role | endpoints | create, delete, get, list, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | namespaces/finalizers | delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | services | * | `config/rbac/role.yaml` |
| rhods-operator-role | deployments, replicasets, services | * | `config/rbac/role.yaml` |
| rhods-operator-role | statefulsets | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | mutatingwebhookconfigurations, validatingadmissionpolicies, validatingadmissionpolicybindings, validatingwebhookconfigurations | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | customresourcedefinitions | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | apiservices | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | deployments, deployments/finalizers, replicasets, statefulsets | * | `config/rbac/role.yaml` |
| rhods-operator-role | workflows | * | `config/rbac/role.yaml` |
| rhods-operator-role | tokenreviews | create, get | `config/rbac/role.yaml` |
| rhods-operator-role | authconfigs | * | `config/rbac/role.yaml` |
| rhods-operator-role | subjectaccessreviews | create, get | `config/rbac/role.yaml` |
| rhods-operator-role | horizontalpodautoscalers | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | machineautoscalers, machinesets | delete, get, list, patch | `config/rbac/role.yaml` |
| rhods-operator-role | cronjobs, jobs/status | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | jobs | * | `config/rbac/role.yaml` |
| rhods-operator-role | buildconfigs | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | buildconfigs/instantiate, builds | create, delete, get, list, patch, watch | `config/rbac/role.yaml` |
| rhods-operator-role | certificates, issuers | create, patch | `config/rbac/role.yaml` |
| rhods-operator-role | codeflares | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | codeflares/status | get | `config/rbac/role.yaml` |
| rhods-operator-role | dashboards, datasciencepipelines, feastoperators, kserves, kueues, llamastackoperators, modelcontrollers, modelmeshservings, modelregistries, rays, trainingoperators, trustyais, workbenches | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | dashboards/finalizers | create, get, list, patch, update, use, watch | `config/rbac/role.yaml` |
| rhods-operator-role | dashboards/status, datasciencepipelines/status, feastoperators/status, kserves/status, kueues/status, llamastackoperators/status, modelcontrollers/status, modelmeshservings/status, modelregistries/status, rays/status, trainingoperators/status, trustyais/status, workbenches/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | datasciencepipelines/finalizers, feastoperators/finalizers, kserves/finalizers, kueues/finalizers, llamastackoperators/finalizers, modelcontrollers/finalizers, modelmeshservings/finalizers, modelregistries/finalizers, rays/finalizers, trainingoperators/finalizers, trustyais/finalizers, workbenches/finalizers | update | `config/rbac/role.yaml` |
| rhods-operator-role | authentications, clusterversions | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | ingresses | get | `config/rbac/role.yaml` |
| rhods-operator-role | consolelinks, odhquickstarts | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | controllermanagerconfigs | create, delete, get, patch | `config/rbac/role.yaml` |
| rhods-operator-role | leases | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | acceleratorprofiles, odhapplications, odhdocuments | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | hardwareprofiles | get, list, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | datascienceclusters | create, delete, deletecollection, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | datascienceclusters/finalizers | patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | datascienceclusters/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | datasciencepipelinesapplications | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | datasciencepipelinesapplications/finalizers, datasciencepipelinesapplications/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | dscinitializations | create, delete, deletecollection, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | dscinitializations/finalizers, dscinitializations/status | delete, get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | events | delete, get, list, patch, watch | `config/rbac/role.yaml` |
| rhods-operator-role | deployments, replicasets | * | `config/rbac/role.yaml` |
| rhods-operator-role | ingresses | delete, get, list, patch, watch | `config/rbac/role.yaml` |
| rhods-operator-role | featuretrackers | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | featuretrackers/finalizers | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | featuretrackers/status | delete, get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | gatewayclasses, gateways, httproutes | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | imagestreams | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | imagestreamtags, registry/metrics | get | `config/rbac/role.yaml` |
| rhods-operator-role | inferencemodels, inferencepools | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | hardwareprofiles | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | hardwareprofiles/finalizers | update | `config/rbac/role.yaml` |
| rhods-operator-role | hardwareprofiles/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | rhmis | delete, get, list, patch, watch | `config/rbac/role.yaml` |
| rhods-operator-role | triggerauthentications | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | kueues | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | kueues/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | clusterqueues, localqueues, resourceflavors | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | clusterqueues/status, localqueues/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | seldondeployments | * | `config/rbac/role.yaml` |
| rhods-operator-role | servicemeshcontrolplanes, servicemeshmemberrolls, servicemeshmembers/finalizers | create, get, list, patch, update, use, watch | `config/rbac/role.yaml` |
| rhods-operator-role | servicemeshmembers | create, delete, get, list, patch, update, use, watch | `config/rbac/role.yaml` |
| rhods-operator-role | nodes, pods | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | modelregistries | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | modelregistries/finalizers | get, update | `config/rbac/role.yaml` |
| rhods-operator-role | modelregistries/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | alertmanagerconfigs, alertmanagers, alertmanagers/finalizers, alertmanagers/status, probes, prometheuses, prometheuses/finalizers, prometheuses/status, thanosrulers, thanosrulers/finalizers, thanosrulers/status | create, delete, deletecollection, get, patch | `config/rbac/role.yaml` |
| rhods-operator-role | podmonitors | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | prometheusrules, servicemonitors | create, delete, deletecollection, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | monitoringstacks, prometheusrules, servicemonitors, thanosqueriers | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | monitoringstacks/finalizers, prometheusrules/finalizers, servicemonitors/finalizers, thanosqueriers/finalizers | update | `config/rbac/role.yaml` |
| rhods-operator-role | monitoringstacks/status, prometheusrules/status, servicemonitors/status, thanosqueriers/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | destinationrules, envoyfilters, gateways, virtualservices | * | `config/rbac/role.yaml` |
| rhods-operator-role | virtualservices/finalizers | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | virtualservices/status | delete, get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | ingresses, networkpolicies | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | oauthclients | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | odhdashboardconfigs | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | instrumentations, opentelemetrycollectors | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | instrumentations/finalizers, opentelemetrycollectors/finalizers | update | `config/rbac/role.yaml` |
| rhods-operator-role | instrumentations/status, opentelemetrycollectors/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | authorinos | * | `config/rbac/role.yaml` |
| rhods-operator-role | knativeservings | * | `config/rbac/role.yaml` |
| rhods-operator-role | knativeservings/finalizers | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | consoles, ingresscontrollers | delete, get, list, patch, watch | `config/rbac/role.yaml` |
| rhods-operator-role | catalogsources, operatorconditions | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | clusterserviceversions | delete, get, list, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | customresourcedefinitions | create, delete, get, patch | `config/rbac/role.yaml` |
| rhods-operator-role | subscriptions | delete, get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | rayclusters | create, delete, get, list, patch | `config/rbac/role.yaml` |
| rhods-operator-role | rayjobs, rayservices | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | clusterrolebindings, clusterroles, rolebindings, roles | * | `config/rbac/role.yaml` |
| rhods-operator-role | routers/federate, routers/metrics | get | `config/rbac/role.yaml` |
| rhods-operator-role | routes | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | authorizationpolicies | * | `config/rbac/role.yaml` |
| rhods-operator-role | securitycontextconstraints | * | `config/rbac/role.yaml` |
| rhods-operator-role | securitycontextconstraints | * | `config/rbac/role.yaml` |
| rhods-operator-role | securitycontextconstraints | * | `config/rbac/role.yaml` |
| rhods-operator-role | auths, monitorings | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | auths/finalizers, gatewayconfigs/finalizers, monitorings/finalizers | update | `config/rbac/role.yaml` |
| rhods-operator-role | auths/status, gatewayconfigs/status, monitorings/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | gatewayconfigs | create, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | services, services/finalizers | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | services/status | delete, get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | clusterservingruntimes, clusterservingruntimes/finalizers, inferencegraphs, inferenceservices, inferenceservices/finalizers, llminferenceserviceconfigs, predictors, servingruntimes/finalizers, trainedmodels | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | clusterservingruntimes/status, inferencegraphs/status, inferenceservices/status, predictors/status, trainedmodels/status | delete, get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | llminferenceserviceconfigs/status, predictors/finalizers, servingruntimes/status | get, patch, update | `config/rbac/role.yaml` |
| rhods-operator-role | llminferenceservices, llminferenceservices/status | get, list, watch | `config/rbac/role.yaml` |
| rhods-operator-role | servingruntimes | * | `config/rbac/role.yaml` |
| rhods-operator-role | volumesnapshots | create, delete, get, patch | `config/rbac/role.yaml` |
| rhods-operator-role | templates | * | `config/rbac/role.yaml` |
| rhods-operator-role | tempomonolithics, tempostacks | create, delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| rhods-operator-role | groups | create, delete, get, list, patch, watch | `config/rbac/role.yaml` |
| rhods-operator-role | users | delete, get, list, patch, update, watch | `config/rbac/role.yaml` |
| auth-editor-role | auths | create, delete, get, list, patch, update, watch | `config/rbac/services_auth_editor_role.yaml` |
| auth-editor-role | auths/status | get | `config/rbac/services_auth_editor_role.yaml` |
| auth-viewer-role | auths | get, list, watch | `config/rbac/services_auth_viewer_role.yaml` |
| auth-viewer-role | auths/status | get | `config/rbac/services_auth_viewer_role.yaml` |
| monitoring-editor-role | monitorings | create, delete, get, list, patch, update, watch | `config/rbac/services_monitoring_editor_role.yaml` |
| monitoring-editor-role | monitorings/status | get | `config/rbac/services_monitoring_editor_role.yaml` |
| monitoring-viewer-role | monitorings | get, list, watch | `config/rbac/services_monitoring_viewer_role.yaml` |
| monitoring-viewer-role | monitorings/status | get | `config/rbac/services_monitoring_viewer_role.yaml` |

### Kubebuilder RBAC Markers

23 markers found in source code.

### Secrets Referenced

| Name | Type | Referenced By |
|------|------|---------------|
| controller-manager-metrics-service | Opaque | deployment/controller-manager |
| kubeflow-training-operator-webhook-cert | Opaque | deployment/training-operator |
| odh-notebook-controller-webhook-cert | kubernetes.io/tls | service/webhook-service |
| dashboard-proxy-tls | Opaque | deployment/odh-dashboard |
| dashboard-oauth-config-generated | Opaque | deployment/odh-dashboard |
| dashboard-oauth-client-generated | Opaque | deployment/odh-dashboard |
| training-operator-webhook-cert | Opaque | deployment/training-operator |
| redhat-ods-operator-controller-webhook-cert | kubernetes.io/tls | deployment/rhods-operator, service/webhook-service |
| webhook-server-cert | Opaque | deployment/manager, deployment/controller-manager, deployment/kuberay-operator |
| kserve-webhook-server-cert | Opaque | deployment/kserve-controller-manager |
| odh-model-controller-webhook-cert | kubernetes.io/tls | deployment/odh-model-controller, service/odh-model-controller-webhook-service |
| modelmesh-webhook-server-cert | Opaque | deployment/modelmesh-controller |

### Container Security Contexts

| Deployment | Container | RunAsNonRoot | ReadOnlyFS | Privileged | Source |
|------------|-----------|--------------|------------|------------|--------|
| odh-dashboard | odh-dashboard | ? | ? | ? | `opt/manifests/dashboard/core-bases/base/deployment.yaml` |
| odh-dashboard | oauth-proxy | ? | ? | ? | `opt/manifests/dashboard/core-bases/base/deployment.yaml` |
| training-operator | training-operator | ? | ? | ? | `opt/manifests/trainingoperator/base/deployment.yaml` |
| odh-dashboard | odh-dashboard | ? | ? | ? | `prefetched-manifests/dashboard/core-bases/base/deployment.yaml` |
| odh-dashboard | oauth-proxy | ? | ? | ? | `prefetched-manifests/dashboard/core-bases/base/deployment.yaml` |
| training-operator | training-operator | ? | ? | ? | `prefetched-manifests/trainingoperator/base/deployment.yaml` |
| workflow-controller | workflow-controller | true | true | ? | `opt/manifests/datasciencepipelines/argo/deployment.workflow-controller.yaml` |
| workflow-controller | workflow-controller | true | true | ? | `prefetched-manifests/datasciencepipelines/argo/deployment.workflow-controller.yaml` |
| rhods-operator | rhods-operator | ? | ? | ? | `config/default/manager_auth_proxy_patch.yaml` |
| rhods-operator | rhods-operator | ? | ? | ? | `config/default/manager_webhook_patch.yaml` |
| rhods-operator | rhods-operator | ? | ? | ? | `config/manager/manager.yaml` |
| manager | manager | ? | ? | ? | `opt/manifests/codeflare/default/manager_webhook_patch.yaml` |
| manager | manager | ? | ? | ? | `opt/manifests/codeflare/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/datasciencepipelines/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/feastoperator/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/feastoperator/manager/manager.yaml` |
| kserve-controller-manager | kube-rbac-proxy | true | true | false | `opt/manifests/kserve/default/manager_auth_proxy_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `opt/manifests/kserve/default/manager_auth_proxy_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `opt/manifests/kserve/default/manager_image_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `opt/manifests/kserve/default/manager_prometheus_metrics_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `opt/manifests/kserve/default/manager_resources_patch.yaml` |
| kserve-localmodel-controller-manager | manager | true | true | false | `opt/manifests/kserve/localmodels/manager.yaml` |
| kserve-controller-manager | manager | true | true | false | `opt/manifests/kserve/manager/manager.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `opt/manifests/kserve/overlays/odh-test/manager_image_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `opt/manifests/kserve/overlays/test/manager_image_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/alpha-enabled/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/components/manager/manager.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `opt/manifests/kueue/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/default/manager_metrics_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/default/manager_visibility_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/default/manager_webhook_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/dev/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/rhoai/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/rhoai/manager_metrics_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/kueue/rhoai/manager_webhook_patch.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `opt/manifests/llamastackoperator/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/llamastackoperator/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/llamastackoperator/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/llamastackoperator/manager/manager.yaml` |
| odh-model-controller | manager | ? | ? | ? | `opt/manifests/modelcontroller/default/manager_webhook_patch.yaml` |
| odh-model-controller | manager | ? | ? | ? | `opt/manifests/modelcontroller/manager/manager.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `opt/manifests/modelmeshserving/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelmeshserving/default/manager_auth_proxy_patch.yaml` |
| modelmesh-controller | manager | ? | ? | ? | `opt/manifests/modelmeshserving/default/manager_webhook_patch.yaml` |
| modelmesh-controller | manager | ? | ? | ? | `opt/manifests/modelmeshserving/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/default/manager_webhook_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/overlays/odh/patches/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/overlays/odh/patches/manager_istio_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/overlays/odh/patches/manager_migration_env_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/modelregistry/overlays/odh/patches/manager_webhook_patch.yaml` |
| kuberay-operator | kuberay-operator | ? | ? | ? | `opt/manifests/ray/default-with-webhooks/manager_webhook_patch.yaml` |
| kuberay-operator | kuberay-operator | ? | ? | ? | `opt/manifests/ray/manager/manager.yaml` |
| training-operator | training-operator | ? | ? | ? | `opt/manifests/trainingoperator/rhoai/manager_config_patch.yaml` |
| training-operator | training-operator | ? | ? | ? | `opt/manifests/trainingoperator/rhoai/manager_metrics_patch.yaml` |
| controller-manager | manager | true | ? | ? | `opt/manifests/trustyai/manager/manager.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/default/manager_image_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/default/manager_prometheus_metrics_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/default/manager_webhook_patch.yaml` |
| deployment | manager | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/manager/manager.yaml` |
| deployment | manager | ? | ? | ? | `opt/manifests/workbenches/kf-notebook-controller/overlays/openshift/manager_openshift_patch.yaml` |
| manager | manager | ? | ? | ? | `opt/manifests/workbenches/odh-notebook-controller/manager/manager.yaml` |
| manager | manager | ? | ? | ? | `prefetched-manifests/codeflare/default/manager_webhook_patch.yaml` |
| manager | manager | ? | ? | ? | `prefetched-manifests/codeflare/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/datasciencepipelines/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/feastoperator/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/feastoperator/manager/manager.yaml` |
| kserve-controller-manager | kube-rbac-proxy | true | true | false | `prefetched-manifests/kserve/default/manager_auth_proxy_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `prefetched-manifests/kserve/default/manager_auth_proxy_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `prefetched-manifests/kserve/default/manager_image_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `prefetched-manifests/kserve/default/manager_prometheus_metrics_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `prefetched-manifests/kserve/default/manager_resources_patch.yaml` |
| kserve-localmodel-controller-manager | manager | true | true | false | `prefetched-manifests/kserve/localmodels/manager.yaml` |
| kserve-controller-manager | manager | true | true | false | `prefetched-manifests/kserve/manager/manager.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `prefetched-manifests/kserve/overlays/odh-test/manager_image_patch.yaml` |
| kserve-controller-manager | manager | ? | ? | ? | `prefetched-manifests/kserve/overlays/test/manager_image_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/alpha-enabled/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/components/manager/manager.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `prefetched-manifests/kueue/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/default/manager_metrics_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/default/manager_visibility_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/default/manager_webhook_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/dev/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/rhoai/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/rhoai/manager_metrics_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/kueue/rhoai/manager_webhook_patch.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `prefetched-manifests/llamastackoperator/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/llamastackoperator/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/llamastackoperator/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/llamastackoperator/manager/manager.yaml` |
| odh-model-controller | manager | ? | ? | ? | `prefetched-manifests/modelcontroller/default/manager_webhook_patch.yaml` |
| odh-model-controller | manager | ? | ? | ? | `prefetched-manifests/modelcontroller/manager/manager.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `prefetched-manifests/modelmeshserving/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelmeshserving/default/manager_auth_proxy_patch.yaml` |
| modelmesh-controller | manager | ? | ? | ? | `prefetched-manifests/modelmeshserving/default/manager_webhook_patch.yaml` |
| modelmesh-controller | manager | ? | ? | ? | `prefetched-manifests/modelmeshserving/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/default/manager_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/default/manager_webhook_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/manager/manager.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/overlays/odh/patches/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/overlays/odh/patches/manager_istio_config_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/overlays/odh/patches/manager_migration_env_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/modelregistry/overlays/odh/patches/manager_webhook_patch.yaml` |
| kuberay-operator | kuberay-operator | ? | ? | ? | `prefetched-manifests/ray/default-with-webhooks/manager_webhook_patch.yaml` |
| kuberay-operator | kuberay-operator | ? | ? | ? | `prefetched-manifests/ray/manager/manager.yaml` |
| training-operator | training-operator | ? | ? | ? | `prefetched-manifests/trainingoperator/rhoai/manager_config_patch.yaml` |
| training-operator | training-operator | ? | ? | ? | `prefetched-manifests/trainingoperator/rhoai/manager_metrics_patch.yaml` |
| controller-manager | manager | true | ? | ? | `prefetched-manifests/trustyai/manager/manager.yaml` |
| controller-manager | kube-rbac-proxy | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/default/manager_auth_proxy_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/default/manager_image_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/default/manager_prometheus_metrics_patch.yaml` |
| controller-manager | manager | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/default/manager_webhook_patch.yaml` |
| deployment | manager | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/manager/manager.yaml` |
| deployment | manager | ? | ? | ? | `prefetched-manifests/workbenches/kf-notebook-controller/overlays/openshift/manager_openshift_patch.yaml` |
| manager | manager | ? | ? | ? | `prefetched-manifests/workbenches/odh-notebook-controller/manager/manager.yaml` |

## Configuration

### ConfigMaps

| Name | Data Keys | Source |
|------|-----------|--------|
| blackbox | blackbox.yml | `config/monitoring/blackbox-exporter/external/blackbox-exporter-external-configmap.yaml` |
| blackbox | blackbox.yml | `config/monitoring/blackbox-exporter/internal/blackbox-exporter-internal-configmap.yaml` |
| workflow-controller-configmap |  | `opt/manifests/datasciencepipelines/argo/configmap.workflow-controller-configmap.yaml` |
| workflow-controller-configmap |  | `prefetched-manifests/datasciencepipelines/argo/configmap.workflow-controller-configmap.yaml` |

## Build

| Path | Base Image | Stages | User | Ports | Architectures | FIPS | Issues |
|------|------------|--------|------|-------|---------------|------|--------|
| `Dockerfiles/Dockerfile` | registry.access.redhat.com/ubi9/ubi-minimal:latest | 3 | 1001 |  | multi-arch |  | Unpinned base image: registry.access.redhat.com/ubi9/toolbox; Unpinned base image: registry.access.redhat.com/ubi9/ubi-minimal:latest |
| `vendor/github.com/itchyny/gojq/Dockerfile` | gcr.io/distroless/static:debug | 2 |  |  |  |  | No USER directive found (defaults to root) |
| `vendor/github.com/pelletier/go-toml/v2/Dockerfile` | scratch | 1 |  |  |  |  | Unpinned base image: scratch; No USER directive found (defaults to root) |
| `Dockerfiles/Dockerfile.konflux` | registry.access.redhat.com/ubi9/ubi-minimal@sha256:7c5495d5fad59aaee12abc3cbbd2b283818ee1e814b00dbc7f25bf2d14fa4f0c | 2 | 1001 |  | multi-arch |  |  |

## Controller Watches

| Type | GVK | Source |
|------|-----|--------|
| For | /v1/ConfigMap | `internal/controller/services/setup/setup_controller.go:45` |
| For | /v1/Secret | `internal/controller/services/secretgenerator/secretgenerator_controller.go:85` |
| Owns | /v1/ConfigMap | `internal/controller/components/kserve/kserve_controller.go:57` |
| Owns | /v1/ConfigMap | `internal/controller/components/ray/ray_controller.go:48` |
| Owns | /v1/ConfigMap | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:28` |
| Owns | /v1/ConfigMap | `internal/controller/components/dashboard/dashboard_controller.go:53` |
| Owns | /v1/ConfigMap | `internal/controller/components/modelregistry/modelregistry_controller.go:49` |
| Owns | /v1/ConfigMap | `internal/controller/components/modelcontroller/modelcontroller_controller.go:50` |
| Owns | /v1/ConfigMap | `internal/controller/components/trainingoperator/trainingoperator_controller.go:45` |
| Owns | /v1/ConfigMap | `internal/controller/components/feastoperator/feastoperator_controller.go:28` |
| Owns | /v1/ConfigMap | `internal/controller/components/kueue/kueue_controller.go:57` |
| Owns | /v1/ConfigMap | `internal/controller/components/modelregistry/modelregistry_controller.go:48` |
| Owns | /v1/ConfigMap | `internal/controller/components/trustyai/trustyai_controller.go:46` |
| Owns | /v1/ConfigMap | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:46` |
| Owns | /v1/ConfigMap | `internal/controller/components/workbenches/workbenches_controller.go:47` |
| Owns | /v1/PersistentVolumeClaim | `internal/controller/dscinitialization/dscinitialization_controller.go:345` |
| Owns | /v1/Secret | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:47` |
| Owns | /v1/Secret | `internal/controller/components/workbenches/workbenches_controller.go:48` |
| Owns | /v1/Secret | `internal/controller/components/kueue/kueue_controller.go:58` |
| Owns | /v1/Secret | `internal/controller/components/dashboard/dashboard_controller.go:54` |
| Owns | /v1/Secret | `internal/controller/components/kserve/kserve_controller.go:55` |
| Owns | /v1/Secret | `internal/controller/components/ray/ray_controller.go:49` |
| Owns | /v1/Secret | `internal/controller/components/modelregistry/modelregistry_controller.go:50` |
| Owns | /v1/Service | `internal/controller/components/ray/ray_controller.go:55` |
| Owns | /v1/Service | `internal/controller/components/workbenches/workbenches_controller.go:54` |
| Owns | /v1/Service | `internal/controller/components/kueue/kueue_controller.go:64` |
| Owns | /v1/Service | `internal/controller/components/trainingoperator/trainingoperator_controller.go:50` |
| Owns | /v1/Service | `internal/controller/components/modelregistry/modelregistry_controller.go:55` |
| Owns | /v1/Service | `internal/controller/components/trustyai/trustyai_controller.go:52` |
| Owns | /v1/Service | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:34` |
| Owns | /v1/Service | `internal/controller/components/feastoperator/feastoperator_controller.go:34` |
| Owns | /v1/Service | `internal/controller/components/dashboard/dashboard_controller.go:60` |
| Owns | /v1/Service | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:53` |
| Owns | /v1/Service | `internal/controller/components/kserve/kserve_controller.go:56` |
| Owns | /v1/Service | `internal/controller/components/modelcontroller/modelcontroller_controller.go:58` |
| Owns | /v1/ServiceAccount | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:52` |
| Owns | /v1/ServiceAccount | `internal/controller/components/workbenches/workbenches_controller.go:53` |
| Owns | /v1/ServiceAccount | `internal/controller/components/dashboard/dashboard_controller.go:59` |
| Owns | /v1/ServiceAccount | `internal/controller/components/feastoperator/feastoperator_controller.go:33` |
| Owns | /v1/ServiceAccount | `internal/controller/components/ray/ray_controller.go:54` |
| Owns | /v1/ServiceAccount | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:33` |
| Owns | /v1/ServiceAccount | `internal/controller/components/trainingoperator/trainingoperator_controller.go:49` |
| Owns | /v1/ServiceAccount | `internal/controller/components/kserve/kserve_controller.go:58` |
| Owns | /v1/ServiceAccount | `internal/controller/components/kueue/kueue_controller.go:63` |
| Owns | /v1/ServiceAccount | `internal/controller/components/trustyai/trustyai_controller.go:47` |
| Owns | /v1/ServiceAccount | `internal/controller/components/modelregistry/modelregistry_controller.go:56` |
| Owns | /v1/ServiceAccount | `internal/controller/components/modelcontroller/modelcontroller_controller.go:51` |
| Owns | admissionregistration.k8s.io/v1/MutatingWebhookConfiguration | `internal/controller/components/kueue/kueue_controller.go:68` |
| Owns | admissionregistration.k8s.io/v1/MutatingWebhookConfiguration | `internal/controller/components/modelregistry/modelregistry_controller.go:58` |
| Owns | admissionregistration.k8s.io/v1/MutatingWebhookConfiguration | `internal/controller/components/kserve/kserve_controller.go:69` |
| Owns | admissionregistration.k8s.io/v1/MutatingWebhookConfiguration | `internal/controller/components/workbenches/workbenches_controller.go:55` |
| Owns | admissionregistration.k8s.io/v1/ValidatingWebhookConfiguration | `internal/controller/components/modelcontroller/modelcontroller_controller.go:59` |
| Owns | admissionregistration.k8s.io/v1/ValidatingWebhookConfiguration | `internal/controller/components/kueue/kueue_controller.go:69` |
| Owns | admissionregistration.k8s.io/v1/ValidatingWebhookConfiguration | `internal/controller/components/modelregistry/modelregistry_controller.go:59` |
| Owns | admissionregistration.k8s.io/v1/ValidatingWebhookConfiguration | `internal/controller/components/kserve/kserve_controller.go:70` |
| Owns | apps/v1/Deployment | `internal/controller/components/modelregistry/modelregistry_controller.go:57` |
| Owns | apps/v1/Deployment | `internal/controller/components/workbenches/workbenches_controller.go:56` |
| Owns | apps/v1/Deployment | `internal/controller/components/kserve/kserve_controller.go:71` |
| Owns | apps/v1/Deployment | `internal/controller/components/trustyai/trustyai_controller.go:53` |
| Owns | apps/v1/Deployment | `internal/controller/components/kueue/kueue_controller.go:70` |
| Owns | apps/v1/Deployment | `internal/controller/components/ray/ray_controller.go:56` |
| Owns | apps/v1/Deployment | `internal/controller/components/dashboard/dashboard_controller.go:64` |
| Owns | apps/v1/Deployment | `internal/controller/components/trainingoperator/trainingoperator_controller.go:51` |
| Owns | apps/v1/Deployment | `internal/controller/components/feastoperator/feastoperator_controller.go:35` |
| Owns | apps/v1/Deployment | `internal/controller/components/modelcontroller/modelcontroller_controller.go:61` |
| Owns | apps/v1/Deployment | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:35` |
| Owns | apps/v1/Deployment | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:55` |
| Owns | components/v1alpha1/Dashboard | `internal/controller/datasciencecluster/datasciencecluster_controller.go:43` |
| Owns | components/v1alpha1/DataSciencePipelines | `internal/controller/datasciencecluster/datasciencecluster_controller.go:50` |
| Owns | components/v1alpha1/FeastOperator | `internal/controller/datasciencecluster/datasciencecluster_controller.go:53` |
| Owns | components/v1alpha1/Kserve | `internal/controller/datasciencecluster/datasciencecluster_controller.go:51` |
| Owns | components/v1alpha1/Kueue | `internal/controller/datasciencecluster/datasciencecluster_controller.go:48` |
| Owns | components/v1alpha1/LlamaStackOperator | `internal/controller/datasciencecluster/datasciencecluster_controller.go:54` |
| Owns | components/v1alpha1/ModelController | `internal/controller/datasciencecluster/datasciencecluster_controller.go:52` |
| Owns | components/v1alpha1/ModelRegistry | `internal/controller/datasciencecluster/datasciencecluster_controller.go:46` |
| Owns | components/v1alpha1/Ray | `internal/controller/datasciencecluster/datasciencecluster_controller.go:45` |
| Owns | components/v1alpha1/TrainingOperator | `internal/controller/datasciencecluster/datasciencecluster_controller.go:49` |
| Owns | components/v1alpha1/TrustyAI | `internal/controller/datasciencecluster/datasciencecluster_controller.go:47` |
| Owns | components/v1alpha1/Workbenches | `internal/controller/datasciencecluster/datasciencecluster_controller.go:44` |
| Owns | console/v1/ConsoleLink | `internal/controller/components/dashboard/dashboard_controller.go:67` |
| Owns | monitoring/v1/PodMonitor | `internal/controller/components/trainingoperator/trainingoperator_controller.go:46` |
| Owns | monitoring/v1/PodMonitor | `internal/controller/components/kueue/kueue_controller.go:66` |
| Owns | monitoring/v1/PrometheusRule | `internal/controller/components/kueue/kueue_controller.go:67` |
| Owns | monitoring/v1/ServiceMonitor | `internal/controller/components/modelcontroller/modelcontroller_controller.go:52` |
| Owns | monitoring/v1/ServiceMonitor | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:54` |
| Owns | monitoring/v1/ServiceMonitor | `internal/controller/components/kserve/kserve_controller.go:68` |
| Owns | networking.k8s.io/v1/NetworkPolicy | `internal/controller/components/kserve/kserve_controller.go:67` |
| Owns | networking.k8s.io/v1/NetworkPolicy | `internal/controller/components/kueue/kueue_controller.go:65` |
| Owns | networking.k8s.io/v1/NetworkPolicy | `internal/controller/components/modelcontroller/modelcontroller_controller.go:53` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:49` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:32` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/workbenches/workbenches_controller.go:50` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/trustyai/trustyai_controller.go:49` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/kserve/kserve_controller.go:61` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/modelcontroller/modelcontroller_controller.go:55` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/ray/ray_controller.go:51` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/feastoperator/feastoperator_controller.go:32` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/trainingoperator/trainingoperator_controller.go:48` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/dashboard/dashboard_controller.go:56` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/services/auth/auth_controller.go:60` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/modelregistry/modelregistry_controller.go:53` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/kueue/kueue_controller.go:60` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/kserve/kserve_controller.go:62` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/modelcontroller/modelcontroller_controller.go:57` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/trainingoperator/trainingoperator_controller.go:47` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/dashboard/dashboard_controller.go:55` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/services/auth/auth_controller.go:59` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/ray/ray_controller.go:50` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/modelregistry/modelregistry_controller.go:54` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:48` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/feastoperator/feastoperator_controller.go:31` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/trustyai/trustyai_controller.go:48` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/kueue/kueue_controller.go:59` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/workbenches/workbenches_controller.go:49` |
| Owns | rbac.authorization.k8s.io/v1/ClusterRoleBinding | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:31` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/kueue/kueue_controller.go:61` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/kserve/kserve_controller.go:59` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/modelcontroller/modelcontroller_controller.go:54` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/services/monitoring/monitoring_controller.go:89` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/trustyai/trustyai_controller.go:50` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:30` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/workbenches/workbenches_controller.go:51` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/services/auth/auth_controller.go:61` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/ray/ray_controller.go:52` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/dashboard/dashboard_controller.go:57` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:50` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/feastoperator/feastoperator_controller.go:30` |
| Owns | rbac.authorization.k8s.io/v1/Role | `internal/controller/components/modelregistry/modelregistry_controller.go:51` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/llamastackoperator/llamastackoperator_controller.go:29` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/ray/ray_controller.go:53` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/services/monitoring/monitoring_controller.go:90` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/trustyai/trustyai_controller.go:51` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/feastoperator/feastoperator_controller.go:29` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/services/auth/auth_controller.go:62` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:51` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/workbenches/workbenches_controller.go:52` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/modelregistry/modelregistry_controller.go:52` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/kserve/kserve_controller.go:60` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/dashboard/dashboard_controller.go:58` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/kueue/kueue_controller.go:62` |
| Owns | rbac.authorization.k8s.io/v1/RoleBinding | `internal/controller/components/modelcontroller/modelcontroller_controller.go:56` |
| Owns | route/v1/Route | `internal/controller/components/dashboard/dashboard_controller.go:66` |
| Owns | route/v1/Route | `internal/controller/services/monitoring/monitoring_controller.go:92` |
| Owns | security/v1/SecurityContextConstraints | `internal/controller/components/ray/ray_controller.go:57` |
| Owns | security/v1/SecurityContextConstraints | `internal/controller/components/datasciencepipelines/datasciencepipelines_controller.go:56` |
| Owns | template/v1/Template | `internal/controller/components/modelcontroller/modelcontroller_controller.go:60` |
| Owns | template/v1/Template | `internal/controller/components/kserve/kserve_controller.go:66` |
| Watches | /v1/Namespace | `internal/controller/components/kueue/kueue_controller.go:119` |
| Watches | /v1/Namespace | `internal/controller/components/modelregistry/modelregistry_controller.go:67` |
| Watches | /v1/Namespace | `internal/controller/components/workbenches/workbenches_controller.go:64` |
| Watches | rbac.authorization.k8s.io/v1/ClusterRole | `internal/controller/components/kueue/kueue_controller.go:113` |
| Watches | services/v1alpha1/Auth | `internal/controller/components/kueue/kueue_controller.go:130` |

## Cache Architecture

### Manager Configuration

| Property | Value |
|----------|-------|
| Manager file | `cmd/main.go` |
| Cache scope | cluster-wide |
| DefaultTransform | yes |
| Memory limit | 4Gi |

### Filtered Types

| Type | Filter Kind | Filter |
|------|-------------|--------|
| corev1.Secret | namespace | namespace-scoped |
| corev1.ConfigMap | namespace | namespace-scoped |
| operatorv1.IngressController | field | field selector |
| configv1.Authentication | field | field selector |
| appsv1.Deployment | namespace | namespace-scoped |
| promv1.PrometheusRule | namespace | namespace-scoped |
| promv1.ServiceMonitor | namespace | namespace-scoped |
| routev1.Route | namespace | namespace-scoped |
| networkingv1.NetworkPolicy | namespace | namespace-scoped |
| rbacv1.Role | namespace | namespace-scoped |
| rbacv1.RoleBinding | namespace | namespace-scoped |

### Cache-Bypassed Types (DisableFor)

- ofapiv1alpha1.Subscription
- authorizationv1.SelfSubjectRulesReview
- corev1.Pod
- userv1.Group
- ofapiv1alpha1.CatalogSource

### Issues

- No GOMEMLIMIT set in deployment (Go GC cannot pressure-tune)
- Type Auth is watched but has no cache filter (cluster-wide informer)
- Type ClusterRole is watched but has no cache filter (cluster-wide informer)
- Type ClusterRoleBinding is watched but has no cache filter (cluster-wide informer)
- Type ConsoleLink is watched but has no cache filter (cluster-wide informer)
- Type Dashboard is watched but has no cache filter (cluster-wide informer)
- Type DataSciencePipelines is watched but has no cache filter (cluster-wide informer)
- Type FeastOperator is watched but has no cache filter (cluster-wide informer)
- Type Kserve is watched but has no cache filter (cluster-wide informer)
- Type Kueue is watched but has no cache filter (cluster-wide informer)
- Type LlamaStackOperator is watched but has no cache filter (cluster-wide informer)
- Type ModelController is watched but has no cache filter (cluster-wide informer)
- Type ModelRegistry is watched but has no cache filter (cluster-wide informer)
- Type MutatingWebhookConfiguration is watched but has no cache filter (cluster-wide informer)
- Type Namespace is watched but has no cache filter (cluster-wide informer)
- Type PersistentVolumeClaim is watched but has no cache filter (cluster-wide informer)
- Type PodMonitor is watched but has no cache filter (cluster-wide informer)
- Type Ray is watched but has no cache filter (cluster-wide informer)
- Type SecurityContextConstraints is watched but has no cache filter (cluster-wide informer)
- Type Service is watched but has no cache filter (cluster-wide informer)
- Type ServiceAccount is watched but has no cache filter (cluster-wide informer)
- Type Template is watched but has no cache filter (cluster-wide informer)
- Type TrainingOperator is watched but has no cache filter (cluster-wide informer)
- Type TrustyAI is watched but has no cache filter (cluster-wide informer)
- Type ValidatingWebhookConfiguration is watched but has no cache filter (cluster-wide informer)
- Type Workbenches is watched but has no cache filter (cluster-wide informer)

