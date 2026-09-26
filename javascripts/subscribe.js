// Upgrades the signup form in overrides/partials/subscribe.html to submit in
// place, so readers stay on the article. Without this script the form still
// works as a plain POST that Kit answers with a redirect.
//
// Material's "navigation.instant" swaps pages without a full reload, so the
// handler is bound through document$, which fires on every page swap.
document$.subscribe(() => {
  const form = document.querySelector(".rvo-subscribe__form")
  if (!form) return

  const status = form.parentElement.querySelector(".rvo-subscribe__status")
  const button = form.querySelector("button")

  form.addEventListener("submit", async (event) => {
    event.preventDefault()
    button.disabled = true
    status.textContent = ""
    status.classList.remove("rvo-subscribe__status--error")

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
      })
      // Kit reports a rejected address as a 200 with status "failed"
      const data = await response.json().catch(() => ({}))
      if (!response.ok || data.status !== "success") {
        throw new Error(data.errors?.messages?.join(" ") || "")
      }
      form.hidden = true
      status.textContent =
        "Almost there! Check your inbox and confirm your subscription."
    } catch (error) {
      status.classList.add("rvo-subscribe__status--error")
      status.textContent =
        error.message || "Something went wrong. Please try again."
      button.disabled = false
    }
  })
})
