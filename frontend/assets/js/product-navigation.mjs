const steps = [
  ["services", "Serviço", "client-services.html"],
  ["professionals", "Profissional", "client-profissional.html"],
  ["date", "Horário", "client-date.html"],
  ["confirm", "Revisão", "client-confirm.html"],
];

// Only local, known destinations and booking identifiers travel between steps.
// In a reschedule the service/professional must remain those of the reservation.
export function bookingNavigation(page, query) {
  const params = new URLSearchParams(query);
  const current = steps.findIndex(([key]) => key === page);
  const rescheduling = Boolean(params.get("appointment_id"));
  const context = new URLSearchParams();
  for (const key of ["service_id", "barbeiro_id", "appointment_id"]) {
    const value = params.get(key);
    if (value) context.set(key, value);
  }
  return steps.map(([key, label, path], index) => {
    let href = null;
    if (index < current && !(rescheduling && index < 2)) {
      if (index === 0) href = path;
      if (index === 1 && context.has("service_id")) {
        href = `${path}?${new URLSearchParams({ service_id: context.get("service_id") })}`;
      }
      if (index === 2 && context.has("service_id") && context.has("barbeiro_id")) href = `${path}?${context}`;
    }
    return { key, label, number: index + 1, current: index === current, complete: index < current, href };
  });
}

export function mountProductNavigation(doc, location) {
  const progress = doc.querySelector("[data-booking-progress]");
  if (progress) {
    const render = () => {
      const query = new URLSearchParams(location.search);
      const service = doc.getElementById("booking-service");
      if (service?.value) query.set("service_id", service.value);
      const items = bookingNavigation(doc.body.dataset.page, query);
      const list = doc.createElement("ol");
      for (const item of items) {
        const li = doc.createElement("li");
        const control = doc.createElement(item.href ? "a" : "span");
        if (item.href) control.href = item.href;
        if (item.current) control.setAttribute("aria-current", "step");
        const number = doc.createElement("span");
        number.className = "step-index";
        number.setAttribute("aria-hidden", "true");
        number.textContent = String(item.number).padStart(2, "0");
        control.append(number, doc.createTextNode(item.label));
        li.classList.toggle("step-complete", item.complete);
        li.append(control);
        list.append(li);
      }
      progress.replaceChildren(list);
      const back = doc.querySelector("[data-booking-back]");
      if (back) {
        const previous = items.filter(item => item.href).at(-1);
        back.href = previous?.href || "client-appointments.html";
      }
    };
    render();
    doc.getElementById("booking-service")?.addEventListener("change", render);
  }

  const accountNav = doc.querySelector(".account-nav");
  if (accountNav) {
    const page = location.pathname.split("/").pop();
    for (const link of accountNav.querySelectorAll("a")) {
      if (link.getAttribute("href") === page) link.setAttribute("aria-current", "page");
    }
  }
}

if (typeof document !== "undefined") mountProductNavigation(document, window.location);
