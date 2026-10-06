import { useEffect, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCheck, faCircleInfo, faFolderOpen, faGamepad, faMap, faPlay, faPuzzlePiece, faSatelliteDish, faTriangleExclamation, faVolumeHigh, faVolumeXmark } from "@fortawesome/free-solid-svg-icons";

const launcherName = "Территория Санька: Королевская Битва";
const fallbackMods = [
  { id: "umcfd", name: "Contact Fuse Drone", description: "Квадрокоптеры с контактным зарядом для всех фракций", exists: false, managed: true, install: { phase: "idle", progress: 0 } },
  { id: "umfc", name: "Канистра с топливом", description: "Подбор канистры и разовая заправка транспорта на 15%", exists: false, managed: true, install: { phase: "idle", progress: 0 } },
];
const fallback = { game: { name: "Arma 3 1.94", exists: false }, mods: fallbackMods, maps: [], launcher: { name: launcherName, version: "1.3.2" } };

function PanelTitle({ icon, children, detail }) {
  return <div className="panel-title"><FontAwesomeIcon icon={icon} aria-hidden="true" /><h2>{children}</h2>{detail ? <span>{detail}</span> : null}</div>;
}

export function App() {
  const [state, setState] = useState(fallback);
  const [notice, setNotice] = useState("Проверяем локальную конфигурацию…");
  const [launching, setLaunching] = useState(false);
  const [gameDir, setGameDir] = useState("");
  const [savingPath, setSavingPath] = useState(false);
  const [soundMuted, setSoundMuted] = useState(false);
  const [update, setUpdate] = useState({ phase: "checking", progress: 0, message: "Проверяем обновления лаунчера…", blocking: true });
  const [enabledMods, setEnabledMods] = useState({ umcfd: true, umfc: true });
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [modChecksPending, setModChecksPending] = useState(true);
  const soundtrack = useRef(null);
  const modInstallAttempted = useRef(new Set());
  const mods = state.mods?.length ? state.mods : fallbackMods;
  const gameFound = state.game.exists && state.game.compatible;
  const isModInstalling = (mod) => mod.install?.phase === "downloading";
  const modInstalling = mods.some(isModInstalling);
  useEffect(() => {
    let active = true;
    const loadStatus = () => fetch("/api/status").then((response) => response.ok ? response.json() : Promise.reject()).then((payload) => {
      if (!active) return;
      setState(payload); setStatusLoaded(true);
      if (payload.ready) setNotice("Готово к запуску в одиночной игре или контролируемой LAN.");
    }).catch(() => active && setNotice("Предпросмотр активен. Для запуска игры откройте launcher.py."));
    const loadUpdate = () => fetch("/api/update/status").then((response) => response.ok ? response.json() : Promise.reject()).then((payload) => {
      if (active) setUpdate(payload);
    }).catch(() => active && setUpdate({ phase: "preview", progress: 0, message: "Автопроверка доступна в локальном лаунчере.", blocking: false }));
    loadStatus();
    loadUpdate();
    const updateTimer = window.setInterval(loadUpdate, 350);
    const statusTimer = window.setInterval(loadStatus, 600);
    return () => { active = false; window.clearInterval(updateTimer); window.clearInterval(statusTimer); };
  }, []);
  useEffect(() => {
    const audio = soundtrack.current;
    if (!audio) return undefined;
    audio.volume = 0.16;
    audio.muted = soundMuted;
    if (!soundMuted) audio.play().catch(() => {});
    return () => audio.pause();
  }, [soundMuted]);
  function toggleSound() {
    setSoundMuted((muted) => !muted);
  }
  function stopSound() {
    soundtrack.current?.pause();
  }
  function toggleMod(modId) {
    setEnabledMods((current) => ({ ...current, [modId]: !current[modId] }));
  }
  async function downloadMod(mod) {
    if (isModInstalling(mod)) return;
    modInstallAttempted.current.add(mod.id);
    setNotice(`Проверяем и загружаем «${mod.name}» из GitHub…`);
    try {
      const response = await fetch(`/api/mod/install/${mod.id}`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Не удалось начать загрузку мода.");
      if (payload.status) setState(payload.status);
      setNotice(payload.message || `Загрузка «${mod.name}» запущена.`);
    } catch (error) { setNotice(error.message || "Не удалось связаться с локальным лаунчером."); }
  }
  useEffect(() => {
    if (!statusLoaded) return;
    const pending = mods.filter((mod) => enabledMods[mod.id] && mod.managed && !isModInstalling(mod) && !modInstallAttempted.current.has(mod.id));
    if (!pending.length) { setModChecksPending(false); return; }
    setModChecksPending(true);
    Promise.all(pending.map(downloadMod)).finally(() => setModChecksPending(false));
  }, [statusLoaded, mods, enabledMods]);
  async function launchGame() {
    stopSound();
    setLaunching(true); setNotice(`Запускаем Arma 3 с «${launcherName}»…`);
    try {
      const enabled_mod_ids = mods.filter((mod) => enabledMods[mod.id]).map((mod) => mod.id);
      const response = await fetch("/api/launch", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled_mod_ids }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Не удалось запустить игру.");
      setNotice(payload.message);
    } catch (error) { setNotice(error.message || "Не удалось связаться с локальным лаунчером."); }
    finally { setLaunching(false); }
  }
  async function saveGamePath(event) {
    event.preventDefault();
    setSavingPath(true); setNotice("Проверяем указанную папку…");
    try {
      const response = await fetch("/api/game-path", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ game_dir: gameDir }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Не удалось сохранить путь.");
      setState(payload.status); setGameDir(""); setNotice(payload.message);
    } catch (error) { setNotice(error.message || "Не удалось связаться с локальным лаунчером."); }
    finally { setSavingPath(false); }
  }
  const unavailableMods = mods.filter((mod) => enabledMods[mod.id] && !mod.exists);
  const enabledNames = mods.filter((mod) => enabledMods[mod.id]).map((mod) => mod.name);
  const canLaunch = gameFound && !unavailableMods.length && !modInstalling && !modChecksPending && !update?.blocking;
  return <main className="app-shell"><section className="launcher" aria-label={`Лаунчер ${launcherName}`}>
    <audio ref={soundtrack} src="/assets/sanyok-soundtrack.mp3" autoPlay loop preload="auto" />
    <header className="hero"><img src="/assets/battlefield-dusk-hero.png" alt="Солдат с парашютом над побережьем на закате" />
      <div className="hero-brand"><div className="brand-kicker">ЛОКАЛЬНЫЙ ЛАУНЧЕР</div><div className="brand-name">ТЕРРИТОРИЯ<br />САНЬКА</div><div className="brand-subtitle">КОРОЛЕВСКАЯ БИТВА · ARMA 3 · GITHUB DELIVERY</div></div>
      <button className={`sound-toggle ${soundMuted ? "muted" : ""}`} type="button" onClick={toggleSound} aria-label={soundMuted ? "Включить фоновую музыку" : "Выключить фоновую музыку"} title={soundMuted ? "Включить музыку" : "Выключить музыку"}><FontAwesomeIcon icon={soundMuted ? faVolumeXmark : faVolumeHigh} aria-hidden="true" /></button>
      <div className="hero-status"><FontAwesomeIcon icon={faSatelliteDish} aria-hidden="true" /><span>ДВА МОДА · БЕЗ КАРТ</span></div>
    </header>
    <div className="content-grid">
      <section className="panel game-panel" aria-label="Игра">
        <PanelTitle icon={faGamepad} detail={gameFound ? `v${state.game.version}` : "требуется v1.94"}>Игра</PanelTitle>
        <div className="game-row"><div className={`game-indicator ${gameFound ? "found" : "not-found"}`} aria-label={gameFound ? "Arma 3 найдена" : "Arma 3 не найдена"}><FontAwesomeIcon icon={gameFound ? faCheck : faTriangleExclamation} aria-hidden="true" /></div><div className="game-copy"><strong>Arma 3</strong><span>{gameFound ? `Найдена · ${state.game.source || "локальный кэш"}` : "Не найдена совместимая копия игры"}</span>{gameFound ? <code>{state.game.path}</code> : null}</div><div className={`availability ${gameFound ? "available" : "missing"}`}>{gameFound ? "Найдена" : "Не найдена"}</div></div>
        <form className="game-path-form" onSubmit={saveGamePath}><label htmlFor="game-dir"><FontAwesomeIcon icon={faFolderOpen} aria-hidden="true" />Папка с Arma 3</label><div><input id="game-dir" value={gameDir} onChange={(event) => setGameDir(event.target.value)} placeholder="Например: D:\\SteamLibrary\\steamapps\\common\\Arma 3" /><button type="submit" disabled={savingPath || !gameDir.trim()}>{savingPath ? "Проверяем…" : "Указать путь"}</button></div><p>При каждом открытии лаунчер проверяет сохранённую папку. Если игра перенесена — ищет её заново.</p></form>
      </section>
      <section className="panel mods-panel" aria-label="Моды"><PanelTitle icon={faPuzzlePiece} detail={`(${mods.length})`}>Моды</PanelTitle>
        <div className="tile-scroll mods-scroll">
          {mods.map((mod) => <article className="mod-row" key={mod.id}><button className={`checkbox ${enabledMods[mod.id] ? "checked" : ""}`} type="button" onClick={() => toggleMod(mod.id)} aria-pressed={Boolean(enabledMods[mod.id])} aria-label={enabledMods[mod.id] ? `Отключить ${mod.name}` : `Включить ${mod.name}`}>{enabledMods[mod.id] ? <FontAwesomeIcon icon={faCheck} aria-hidden="true" /> : null}</button><div className="mod-mark"><FontAwesomeIcon icon={faSatelliteDish} aria-hidden="true" /></div><div className="mod-copy"><strong>{mod.name}</strong><span>{mod.description}</span>{enabledMods[mod.id] && mod.install?.message ? <small>{mod.install.message}</small> : null}</div><div className={`availability ${mod.exists ? "available" : "missing"}`}>{isModInstalling(mod) ? "Загрузка…" : mod.exists ? "Готов" : enabledMods[mod.id] ? "Не найден" : "Отключён"}</div></article>)}
          <p className="panel-footnote"><FontAwesomeIcon icon={faCircleInfo} aria-hidden="true" />{unavailableMods.length ? <>Отмеченные моды проверяются и при необходимости скачаются из GitHub в локальную папку лаунчера. <button className="inline-action" type="button" onClick={() => unavailableMods.forEach(downloadMod)} disabled={modInstalling}>Повторить</button></> : "При запуске отмеченные моды сверяются с GitHub и обновляются только в папке лаунчера."}</p>
        </div>
      </section>
      <section className="panel maps-panel" aria-label="Карты"><PanelTitle icon={faMap} detail="(0)">Карты</PanelTitle><div className="tile-scroll maps-scroll"><div className="empty-maps"><FontAwesomeIcon icon={faMap} aria-hidden="true" /><strong>Карты пока не подключены</strong><span>Поле намеренно оставлено пустым.</span></div></div></section>
    </div>
    <section className="update-area" aria-label="Обновление лаунчера"><div className="update-heading"><strong>Обновление лаунчера</strong><span>{update?.latest_version ? `Версия ${update.latest_version}` : `Текущая версия ${state.launcher?.version || fallback.launcher.version}`}</span></div><div className="update-meter" role="progressbar" aria-label="Ход обновления" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.max(0, Math.min(100, update?.progress || 0))}><span style={{ width: `${Math.max(0, Math.min(100, update?.progress || 0))}%` }} /></div><p role="status">{update?.message || "Проверяем обновления лаунчера…"}</p></section>
    <footer className="launch-area"><p className="launch-status" role="status">{update?.blocking ? "Сначала завершается обязательная проверка обновления…" : modInstalling ? mods.find(isModInstalling)?.install?.message : notice}</p><button className="launch-button" onClick={launchGame} disabled={launching || !canLaunch}><FontAwesomeIcon icon={faPlay} aria-hidden="true" /><span>{launching ? "Запуск…" : "Играть"}</span></button><p className="launch-note">{gameFound ? `${state.game.name} · ${enabledNames.length ? enabledNames.join(" + ").toUpperCase() : "БЕЗ МОДОВ"} · -world=empty` : "Укажите папку с Arma 3 1.94, чтобы продолжить"}</p></footer>
  </section></main>;
}
