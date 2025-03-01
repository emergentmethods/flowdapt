from flowdapt.triggers.domain.dto.v1.triggerrule import (
    V1Alpha1TriggerRuleResourceCreateRequest,
    V1Alpha1TriggerRuleResourceCreateResponse,
    V1Alpha1TriggerRuleResourceReadResponse,
    V1Alpha1TriggerRuleResourceUpdateRequest,
    V1Alpha1TriggerRuleResourceUpdateResponse,
)


TriggerRuleResourceCreateRequest = V1Alpha1TriggerRuleResourceCreateRequest
TriggerRuleResourceCreateResponse = V1Alpha1TriggerRuleResourceCreateResponse
TriggerRuleResourceUpdateRequest = V1Alpha1TriggerRuleResourceUpdateRequest
TriggerRuleResourceUpdateResponse = V1Alpha1TriggerRuleResourceUpdateResponse
TriggerRuleResourceReadResponse = V1Alpha1TriggerRuleResourceReadResponse


TriggerRuleCreateDTOs = {
    "v1alpha1": (
        V1Alpha1TriggerRuleResourceCreateRequest,
        V1Alpha1TriggerRuleResourceCreateResponse,
    ),
}

TriggerRuleUpdateDTOs = {
    "v1alpha1": (
        V1Alpha1TriggerRuleResourceUpdateRequest,
        V1Alpha1TriggerRuleResourceUpdateResponse,
    ),
}

TriggerRuleReadDTOs = {
    "v1alpha1": (None, V1Alpha1TriggerRuleResourceReadResponse),
}
