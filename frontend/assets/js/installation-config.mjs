// Per-install frontend endpoint. Set this to the public HTTPS API origin.
export const INSTALLATION_CONFIG = Object.freeze({
  apiBaseUrl: "http://127.0.0.1:8000",
  brand: Object.freeze({
    name: "Barbearia",
    mark: "B.",
    tagline: "ESTILO COM ATITUDE",
    logoUrl: "",
    themeColor: "#15120f",
  }),
  content: Object.freeze({
    homeHeroEyebrow: "Seu próximo visual começa aqui",
    homeHeroTitleLead: "O clássico nunca sai de",
    homeHeroTitleAccent: "cena.",
    homeHeroDescription: "Cuidado de verdade, conversa boa e um corte feito para você. Escolha seu serviço e reserve seu horário sem complicação.",
    homePrimaryAction: "Escolher meu horário",
    homeSecondaryAction: "Explorar serviços",
    homeFooterMessage: "Um bom corte muda o dia.",
    consentText: "Li e aceito os Termos de Uso e estou ciente da Política de Privacidade.",
  }),
  // Dados do controlador exibidos no rodapé e nos documentos legais.
  // Preencha com os dados reais da empresa; campos vazios aparecem como "Não informado".
  legal: Object.freeze({
    razaoSocial: "",
    cnpj: "",
    endereco: "",
    email: "",
    telefone: "",
    encarregadoNome: "",
    encarregadoEmail: "",
    documentosAtualizadosEm: "2026-11-18",
    versaoDocumentos: "1.0",
  }),
  features: Object.freeze({
    estrelinhaWidget: true,
  }),
});
