(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('.theme-control');
  const syncTheme = () => {
    const dark = root.dataset.theme === 'dark';
    themeButton?.setAttribute('aria-label', dark ? '밝은 테마로 전환' : '어두운 테마로 전환');
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0c1425' : '#f7f9fc');
  };
  if (themeButton) {
    themeButton.hidden = false;
    syncTheme();
    themeButton.addEventListener('click', () => {
      root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('theme', root.dataset.theme); } catch (_) {}
      syncTheme();
    });
  }
  document.querySelectorAll('.prose table').forEach(table => {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll';
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', '표 — 좌우로 스크롤할 수 있습니다');
    table.before(wrapper);
    wrapper.append(table);
  });
  if (navigator.clipboard && window.isSecureContext) {
    document.querySelectorAll('.prose pre').forEach(pre => {
      const code = pre.querySelector('code');
      if (!code) return;
      const button = document.createElement('button');
      button.className = 'copy-code';
      button.type = 'button';
      button.textContent = '복사';
      button.setAttribute('aria-label', '코드 복사');
      button.addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(code.textContent); button.textContent = '복사 완료'; }
        catch (_) { button.textContent = '복사 실패'; }
        setTimeout(() => { button.textContent = '복사'; }, 1800);
      });
      pre.append(button);
    });
  }
})();
