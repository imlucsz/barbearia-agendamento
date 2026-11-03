# HOME — decisões confirmadas

- A HOME segue uma direção cinematográfica, editorial e premium.
- GSAP é a engine principal de motion.
- O Ritual aprovado usa o vídeo como palco da composição, com tipografia HTML sobre o filme; preservar o scrub e os pontos narrativos aprovados.
- Com `prefers-reduced-motion: no-preference`, o Ritual usa scrub contínuo de 0 a 1 em todas as larguras/alturas, inclusive mobile e landscape. Breakpoints podem adaptar pin, crop, textos e distância de scroll; nunca selecionar três stills. Preservar `progressToTime`, fila segura de seeks e cortes narrativos em 2,5s/7,75s.
- Reduced-motion é obrigatório, com conteúdo completo e alternativa estática para o Ritual.
- Conteúdo comercial e dinâmico, estados de carregamento/erro/vazio, navegação, autenticação e links reais de agendamento não podem ser perdidos pela apresentação visual.
- A Estrelinha será inicialmente uma mascote cinematográfica de assinatura, não chatbot ou assistente.
- Sua primeira fase tem no máximo três aparições raras e intencionais: pós-hero, cameo intermediário e fechamento próximo ao CTA, sem competir com o conteúdo principal.
- Evolução funcional futura da Estrelinha está fora desta fase.

Evidências de implementação e validação existentes: [HOME](../docs/HOME_MOTION_INTEGRATION.md) e [Estrelinha](../docs/ESTRELINHA_CINEMATICA.md). Este registro não cria funcionalidades nem autoriza publicação.
