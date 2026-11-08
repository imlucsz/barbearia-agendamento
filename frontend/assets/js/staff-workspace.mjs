export const staffAreas = [
  { label: 'Agenda', sections: ['agenda', 'agendamento-manual'] },
  { label: 'Clientes', sections: ['clientes'] },
  { label: 'Equipe e horários', sections: ['equipe', 'jornadas'] },
  { label: 'Serviços', sections: ['servicos'] },
  { label: 'Financeiro', sections: ['financeiro'] },
  { label: 'Configurações', sections: ['institucional', 'avaliacoes', 'auditoria'] },
];
export function staffDestination(hash, role) {
  const section = String(hash).replace(/^#/, '');
  const area = staffAreas.find(area => area.sections.includes(section));
  return role === 'admin' && area ? section : 'agenda';
}

export function initializeWorkspace(user) {
  const body = document.body;
  const titles = { agenda: user.role === 'barbeiro' ? 'Minha agenda' : 'Agenda da barbearia', 'agendamento-manual': 'Novo agendamento', clientes: 'Clientes', equipe: 'Serviços por profissional', jornadas: 'Horários de trabalho e folgas', servicos: 'Serviços', financeiro: 'Financeiro', institucional: 'Informações da barbearia', avaliacoes: 'Avaliações dos clientes', auditoria: 'Histórico de atividades' };
  const descriptions = { agenda: user.role === 'barbeiro' ? 'Seus atendimentos, organizados por dia. Selecione um horário para concluir ou atualizar.' : 'Acompanhe os atendimentos da equipe e registre as reservas recebidas por telefone ou no balcão.', jornadas: 'Defina o expediente semanal e os períodos em que cada profissional não atende.', financeiro: 'Consulte o período e os valores dos atendimentos concluídos.', servicos: 'Consulte o catálogo, adicione um serviço ou edite os dados existentes.' };
  body.dataset.staffRole = user.role;
  body.dataset.staffReady = 'true';
  document.getElementById('staff-role').textContent = user.role === 'admin' ? 'ADMINISTRAÇÃO' : 'ÁREA DO BARBEIRO';
  function activate(focus = false) {
    const section = staffDestination(location.hash, user.role);
    if (location.hash !== '#' + section) history.replaceState(null, '', '#' + section);
    const area = staffAreas.find(area => area.sections.includes(section));
    for (const panel of document.querySelectorAll('.admin-section')) panel.hidden = panel.id !== section;
    for (const link of document.querySelectorAll('[data-staff-area]')) {
      link.hidden = user.role !== 'admin' && link.dataset.staffArea !== 'agenda';
      if (area.sections.includes(link.dataset.staffArea)) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    for (const nav of document.querySelectorAll('[data-staff-subnav]')) {
      nav.hidden = user.role !== 'admin' || nav.dataset.staffSubnav !== area.sections[0];
      for (const link of nav.querySelectorAll('a')) {
        if (link.hash === '#' + section) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      }
    }
    const title = document.getElementById('staff-title');
    title.textContent = titles[section];
    document.getElementById('staff-description').textContent = descriptions[section] || 'Consulte os registros e escolha a ação que deseja realizar.';
    document.title = `${titles[section]} | Barbearia`;
    if (focus) title.focus({ preventScroll: true });
  }
  activate();
  window.addEventListener('hashchange', () => activate(true));

  // Keep lists visible; reveal only the editor that the user asks to use.
  for (const [formId, cancelId, createLabel, editLabel] of [
    ['service-form', 'service-cancel-edit', 'Adicionar serviço', 'Editar serviço'],
    ['schedule-form', 'schedule-cancel-edit', 'Adicionar horário semanal', 'Editar horário semanal'],
    ['block-form', 'block-cancel-edit', 'Adicionar folga ou bloqueio', 'Editar folga ou bloqueio'],
  ]) {
    const form = document.getElementById(formId);
    const editor = form.closest('details');
    const cancel = document.getElementById(cancelId);
    const summary = editor.querySelector('summary');
    const sync = () => {
      const editing = !cancel.hidden;
      summary.textContent = editing ? editLabel : createLabel;
      form.dataset.mode = editing ? 'edit' : 'create';
      if (editing) {
        editor.open = true;
        form.querySelector('input:not([type=hidden]):not([disabled]), select:not([disabled])')?.focus({ preventScroll: true });
      }
    };
    new MutationObserver(sync).observe(cancel, { attributes: true, attributeFilter: ['hidden'] });
    cancel.addEventListener('click', () => { editor.open = false; summary.focus(); });
    sync();
  }
}
