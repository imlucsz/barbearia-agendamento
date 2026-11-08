# Compatibilidade do frontend

O frontend usa HTML, CSS e JavaScript ES Modules nativos. As páginas carregam arquivos com `<script type="module">` e imports relativos; o projeto não tem etapa de build, bundler ou transpilação. A home também usa import maps para carregar Three.js pelo jsDelivr.

O CI executa verificações de layout e acessibilidade nos motores Chromium, Firefox e WebKit, em 320×568, 390×844 e 1280×800. Chromium e WebKit são referências para os motores usados por Chrome/Edge e Safari, respectivamente; o CI não instala as versões de marca Chrome, Edge ou Safari. A validação de marca e versões estáveis deve ser feita antes de uma declaração formal de compatibilidade desses produtos.

Navegadores antigos sem suporte a módulos ES (como Internet Explorer 11 e versões antigas do Edge) não carregam os scripts da aplicação. Import maps chegaram mais tarde: o Three.js da home depende de navegador com suporte a import maps; em versões antigas, a Estrelinha não inicia mesmo quando módulos ES são suportados. O projeto não fornece bundle legado nem fallback/transpilação.

Consulte a [referência de módulos JavaScript da MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules) e a [tabela de suporte a import maps](https://caniuse.com/import-maps) para requisitos por navegador.
