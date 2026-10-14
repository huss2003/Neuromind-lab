import { useEffect, useRef } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

const SUFFIX = 'NeuroMind Lab';

/** Single-page apps must do what a page load does for assistive technology: give each screen its own document title and move focus
 *  to the new content after in-app navigation (otherwise a screen reader keeps reading from the link that was clicked). */
export function RouteA11y() {
  const { pathname } = useLocation();
  const navType = useNavigationType();
  const first = useRef(true);

  useEffect(() => {
    const setTitle = () => {
      const h1 = document.querySelector('h1')?.textContent?.trim();
      const next = h1 ? `${h1} · ${SUFFIX}` : SUFFIX;
      if (document.title !== next) document.title = next;
    };
    let frame = 0;
    const observer = new MutationObserver(() => { cancelAnimationFrame(frame); frame = requestAnimationFrame(setTitle); });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    setTitle();
    return () => { observer.disconnect(); cancelAnimationFrame(frame); };
  }, []);

  useEffect(() => {
    if (first.current) { first.current = false; return; } // a fresh page load already starts at the top
    if (navType === 'REPLACE') return; // automatic redirects (e.g. signed-out visitor sent to sign-in) are not a user navigation: keep the skip link first in the tab order
    const target = document.getElementById('main') ?? document.querySelector<HTMLElement>('main');
    if (!target) return;
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
    target.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }, [pathname, navType]);

  return null;
}
