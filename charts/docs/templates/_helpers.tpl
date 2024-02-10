{{- define "middleware-annotation" }}
{{- $first := true -}}
{{- range $i, $middleware := .Values.ingress.middlewares -}}
{{- if $first -}}{{- $first = false -}}{{- else -}},{{- end -}}
{{- if contains "/" $middleware -}}
{{- $middleware = replace "/" "-" $middleware -}}
{{- else -}}
{{- $middleware = printf "%s-%s" $.Release.Namespace $middleware -}}
{{- end -}}
{{- printf "%s@kubernetescrd" $middleware -}}
{{- end -}}
{{- end -}}