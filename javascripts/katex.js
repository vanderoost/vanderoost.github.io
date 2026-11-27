document$.subscribe(({ body }) => {
  for (const el of body.querySelectorAll(".arithmatex")) {
    renderMathInElement(el, {
      delimiters: [
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
    });
  }
});
