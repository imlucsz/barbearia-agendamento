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
    consentText: "Li e aceito o tratamento dos meus dados pessoais para cadastro e gestão dos agendamentos.",
  }),
  features: Object.freeze({
    estrelinhaWidget: true,
  }),
});
