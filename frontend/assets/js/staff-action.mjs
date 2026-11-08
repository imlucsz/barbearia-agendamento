const actions = {
  concluido: { title: 'Concluir atendimento', button: 'Confirmar conclusão', description: 'Confira o valor cobrado. Ele será registrado junto ao atendimento.' },
  falta: { title: 'Marcar ausência', button: 'Confirmar ausência', description: 'Confirme que o cliente não compareceu a este atendimento.' },
  cancelado: { title: 'Cancelar agendamento', button: 'Confirmar cancelamento', description: 'O horário será cancelado. Confira os dados antes de continuar.' },
};

export function openStaffAction({ appointment, status, dateLabel, opener, isCurrent, submit }) {
  const action = actions[status];
  const dialog = document.getElementById('staff-action-dialog');
  if (!action || dialog.open) return;
  const form = dialog.querySelector('form');
  const confirm = form.querySelector('[type=submit]');
  const cancel = dialog.querySelector('[data-dialog-cancel]');
  const amount = document.getElementById('staff-action-amount');
  const error = document.getElementById('staff-action-error');
  let pending = false;
  document.getElementById('staff-action-title').textContent = action.title;
  document.getElementById('staff-action-description').textContent = action.description;
  document.getElementById('staff-action-context').textContent = `${appointment.cliente} · ${appointment.servico} · ${dateLabel} às ${appointment.horario}`;
  document.getElementById('staff-action-value').hidden = status !== 'concluido';
  amount.disabled = status !== 'concluido';
  amount.value = String(appointment.valorCobrado ?? appointment.preco);
  error.hidden = true;
  confirm.textContent = action.button;
  confirm.className = status === 'cancelado' ? 'btn btn-danger' : 'btn';
  confirm.disabled = false;
  cancel.disabled = false;
  cancel.onclick = () => { if (!pending) dialog.close(); };
  dialog.oncancel = event => { if (pending) event.preventDefault(); };
  dialog.onclose = () => { if (opener.isConnected) opener.focus(); };
  form.onsubmit = async event => {
    event.preventDefault();
    if (pending) return;
    error.hidden = true;
    const body = { status };
    if (status === 'concluido') {
      const value = amount.value.trim();
      if (!value || !Number.isFinite(Number(value)) || Number(value) < 0) {
        error.textContent = 'Informe o valor cobrado, igual ou maior que zero.';
        error.hidden = false;
        amount.focus();
        return;
      }
      body.valor_cobrado = Number(value);
    }
    if (!isCurrent()) {
      error.textContent = 'A agenda mudou. Feche esta janela e selecione o atendimento novamente.';
      error.hidden = false;
      return;
    }
    pending = true;
    confirm.disabled = true;
    cancel.disabled = true;
    amount.disabled = true;
    form.setAttribute('aria-busy', 'true');
    confirm.textContent = 'Salvando…';
    try {
      await submit(body);
      dialog.close();
      // The successful refresh replaces the row. Restore a useful keyboard target.
      if (!opener.isConnected) document.getElementById('agenda-title')?.focus({ preventScroll: true });
    } catch (failure) {
      error.textContent = failure.message || 'Não foi possível salvar. Tente novamente.';
      error.hidden = false;
      error.focus();
    } finally {
      pending = false;
      confirm.disabled = false;
      cancel.disabled = false;
      amount.disabled = status !== 'concluido';
      confirm.textContent = action.button;
      form.removeAttribute('aria-busy');
    }
  };
  dialog.showModal();
  cancel.focus();
}
