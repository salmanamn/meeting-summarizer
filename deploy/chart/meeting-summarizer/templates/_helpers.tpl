{{/* The image, always by digest (the platform's admission policy wants a version; this chart wants the digest). */}}
{{- define "meeting.image" -}}
{{- $repository := required "image.repository is required (the platform's registry)" .Values.image.repository -}}
{{- $digest := required "image.digest is required (sha256:...)" .Values.image.digest -}}
{{- if not (regexMatch "^sha256:[0-9a-f]{64}$" $digest) -}}
{{- fail (printf "image.digest must be sha256:<64 hex>, got %q" $digest) -}}
{{- end -}}
{{ $repository }}@{{ $digest }}
{{- end -}}

{{- define "meeting.labels" -}}
app.kubernetes.io/name: meeting-summarizer
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "meeting.selector" -}}
app.kubernetes.io/name: meeting-summarizer
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Pod Security "restricted", no Kubernetes API token (the platform's rules, D7 and D9 there). */}}
{{- define "meeting.podSecurity" -}}
automountServiceAccountToken: false
enableServiceLinks: false
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault
{{- end -}}

{{- define "meeting.containerSecurity" -}}
allowPrivilegeEscalation: false
capabilities:
  drop: [ALL]
{{- end -}}

{{/* python3 -m meeting.fetch_job finds the app's packages and the app (the Functions host sets these itself). */}}
{{- define "meeting.pythonPath" -}}
- name: PYTHONPATH
  value: /home/site/wwwroot/.python_packages/lib/site-packages:/home/site/wwwroot
- name: MODELS_DIR
  value: /models
{{- end -}}

{{/* A Functions host loading only the given functions. dict: root, functions, resources, ready (readiness path),
models (mount the models read-only after checking them). The host answers /admin/host/ping without a key;
/api/health (anonymous) only once the Python worker has indexed. */}}
{{- define "meeting.functionsPod" -}}
{{- $root := .root -}}
{{ include "meeting.podSecurity" $root }}
{{- if .models }}
initContainers:
  - name: check-models
    image: {{ include "meeting.image" $root }}
    imagePullPolicy: IfNotPresent
    command: ["python3", "-m", "meeting.fetch_job", "check", {{ range $i, $n := $root.Values.models.names }}{{ if $i }}, {{ end }}{{ $n | quote }}{{ end }}]
    env:
      {{- include "meeting.pythonPath" $root | nindent 6 }}
    securityContext:
      {{- include "meeting.containerSecurity" $root | nindent 6 }}
      readOnlyRootFilesystem: true
    resources:
      {{- toYaml $root.Values.models.resources | nindent 6 }}
    volumeMounts:
      - name: models
        mountPath: /models
        readOnly: true
{{- end }}
containers:
  - name: functions
    image: {{ include "meeting.image" $root }}
    imagePullPolicy: IfNotPresent
    ports:
      - name: http
        containerPort: 8080
    envFrom:
      - configMapRef:
          name: {{ $root.Release.Name }}-config
    env:
      {{- range $i, $name := .functions }}
      - name: AzureFunctionsJobHost__functions__{{ $i }}
        value: {{ $name | quote }}
      {{- end }}
      {{- range $root.Values.secretSettings.keys }}
      - name: {{ . }}
        valueFrom:
          secretKeyRef:
            name: {{ $root.Values.secretSettings.secretName }}
            key: {{ . }}
      {{- end }}
    securityContext:
      {{- include "meeting.containerSecurity" $root | nindent 6 }}
    resources:
      {{- toYaml .resources | nindent 6 }}
    startupProbe:
      httpGet: { path: /admin/host/ping, port: http }
      periodSeconds: 5
      failureThreshold: 36
    readinessProbe:
      httpGet: { path: {{ .ready }}, port: http }
      periodSeconds: 10
    livenessProbe:
      httpGet: { path: /admin/host/ping, port: http }
      periodSeconds: 20
      timeoutSeconds: 5
    volumeMounts:
      - name: function-keys
        mountPath: /run/secrets/functions-keys
        readOnly: true
      {{- if .models }}
      - name: models
        mountPath: /models
        readOnly: true
      {{- end }}
volumes:
  - name: function-keys
    secret:
      secretName: {{ $root.Values.functionKeys.secretName }}
  {{- if .models }}
  - name: models
    persistentVolumeClaim:
      claimName: {{ $root.Release.Name }}-models
      readOnly: true
  {{- end }}
{{- end -}}