# Monitoramento e operação (RNF-17)

## Health e readiness

- `GET /health` verifica a conectividade atual com o banco usando `SELECT 1`. A chamada aguarda no máximo 1 segundo e responde `503` com mensagem genérica se o banco não responder. Use esta rota para detectar indisponibilidade do processo ou do banco.
- `GET /ready` verifica conectividade e se a revisão Alembic aplicada corresponde à versão esperada pela aplicação. Retorna `503` também quando o schema precisa de atualização; nunca executa migrações. Use-a para decidir se a instância pode receber tráfego após uma atualização.

Nenhuma rota inclui URL, erro de driver, credenciais ou detalhes internos na resposta. Não coloque tokens nas URLs de health checks.

## Verificação externa a cada minuto

Configure o monitor em um host externo à API e ao banco. Monitore `https://api.seu-dominio/health`, aceite somente HTTP 200 e configure alerta após 3 falhas consecutivas (cerca de 3 minutos com cadência de 1 minuto). Envie alertas por e-mail ou pelo canal operacional já adotado pela instalação.

Exemplo gratuito: [UptimeRobot Free](https://help.uptimerobot.com/en/articles/11604710-who-should-use-uptimerobot-s-free-plan) oferece monitor HTTP e alertas, mas atualmente verifica a cada 5 minutos. Portanto, não atende sozinho à cadência de 1 minuto; use-o se 5 minutos forem aceitáveis ou use a alternativa cron abaixo. A oferta gratuita e os intervalos podem mudar; confirme as condições no fornecedor antes de criar a conta.

Alternativa cron em uma máquina externa Linux. Salve o script abaixo como `/usr/local/bin/check-barbearia-health.sh`, ajuste `HEALTH_URL` e integre a seção de alerta ao comando de notificação da instalação. O contador evita alertas repetidos e alerta depois de três falhas seguidas; uma resposta saudável rearma o alerta.

```sh
#!/bin/sh
set -eu

HEALTH_URL="https://api.seu-dominio/health"
STATE_FILE="/var/tmp/barbearia-health-failures"
ALERT_FILE="/var/tmp/barbearia-health-alerted"

if curl --silent --show-error --fail --max-time 5 "$HEALTH_URL" >/dev/null; then
  rm -f "$STATE_FILE" "$ALERT_FILE"
  exit 0
fi

failures=0
if [ -r "$STATE_FILE" ]; then
  failures=$(cat "$STATE_FILE")
fi
failures=$((failures + 1))
printf '%s\n' "$failures" > "$STATE_FILE"

if [ "$failures" -ge 3 ] && [ ! -e "$ALERT_FILE" ]; then
  logger -p user.crit -t barbearia-health "health endpoint failed 3 consecutive checks"
  # Add the site's approved email or webhook notification command here.
  : > "$ALERT_FILE"
fi
```

Adicione ao crontab do usuário de monitoramento:

```cron
* * * * * /usr/bin/flock -n /var/tmp/barbearia-health.lock /usr/local/bin/check-barbearia-health.sh
```

O script não envia notificação por si só; `logger` deixa o evento disponível ao agente de monitoração do host. Configure esse agente ou substitua o comentário pelo mecanismo de alerta da instalação. Mantenha esse host e o canal de notificação fora da máquina monitorada.

## Métricas Prometheus

`GET /metrics` expõe métricas agregadas em memória por processo. Configure `METRICS_TOKEN` com pelo menos 32 caracteres aleatórios; sem essa variável a rota responde `404`. Com token, use `Authorization: Bearer ...`. Nunca passe o token em query string, nem o inclua no repositório ou em logs.

As métricas incluem contagem por template de rota, método e status; proporção de respostas 5xx; e quantis aproximados p50/p95 de latência, calculados sobre as últimas 2048 observações de cada rota/método. Os rótulos não contêm query string, IP, usuário ou identificadores de recursos. Os dados reiniciam com o processo. Em execução com vários workers, cada worker mantém seu próprio conjunto; configure coleta direta por worker ou use um único worker quando precisar interpretar essas métricas por instância.

Exemplo de scrape com arquivo de credenciais protegido pelo sistema operacional:

```yaml
scrape_configs:
  - job_name: barbearia-api
    metrics_path: /metrics
    scrape_interval: 30s
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/secrets/barbearia-metrics-token
    static_configs:
      - targets: ["api.seu-dominio:443"]
    scheme: https
```

Exemplo de regra de alerta se mais de 5% das respostas em cinco minutos forem 5xx, com volume mínimo para evitar alertar sobre uma única chamada:

```yaml
groups:
  - name: barbearia-api
    rules:
      - alert: BarbeariaApiHigh5xxRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / clamp_min(sum(rate(http_requests_total[5m])), 0.001) > 0.05
          and sum(rate(http_requests_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: Taxa elevada de respostas 5xx na API da barbearia
```

O destino e o receptor de alertas são configuração operacional do ambiente; este repositório não cria contas, recursos pagos ou configuração de deploy.
