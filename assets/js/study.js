(() => {
  const archive = document.querySelector('[data-study-search]');
  if (!archive) return;

  const controls = archive.querySelector('[data-study-search-controls]');
  const input = archive.querySelector('[data-study-search-input]');
  const count = archive.querySelector('[data-study-search-count]');
  const empty = archive.querySelector('[data-study-search-empty]');
  const episodes = Array.from(archive.querySelectorAll('[data-study-episode]'));
  const normalize = (value) => value.normalize('NFKC').toLocaleLowerCase().trim();

  const update = () => {
    const terms = normalize(input.value).split(/\s+/).filter(Boolean);
    let visible = 0;
    episodes.forEach((episode) => {
      const text = normalize(episode.dataset.studySearchText);
      const matches = terms.every((term) => text.includes(term));
      episode.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = terms.length ? `${visible}개 / 전체 ${episodes.length}개` : `전체 ${episodes.length}개`;
    empty.hidden = visible !== 0;
  };

  controls.hidden = false;
  input.addEventListener('input', update);
  update();
})();
