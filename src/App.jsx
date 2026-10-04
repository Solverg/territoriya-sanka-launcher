import { useEffect, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowsRotate, faCheck, faCircleInfo, faDownload, faFolderOpen, faGamepad, faMap, faPlay, faPuzzlePiece, faSatelliteDish, faTriangleExclamation, faVolumeHigh, faVolumeXmark } from "@fortawesome/free-solid-svg-icons";

const launcherName = "Территория Санька: Королевская Битва";
const fallback = { game: { name: "Arma 3 1.94", exists: false }, mods: [{ name: "Contact Fuse Drone", description: "Квадрокоптеры с контактным зарядом для всех фракций", exists: false }], maps: [], launcher: { name: launcherName, version: "0.1.0" } };

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
  const [update, setUpdate] = useState(null);
  const [updating, setUpdating] = useState(false);
  const soundtrack = useRef(null);
  useEffect(() => {
    fetch("/api/status").then((response) => response.ok ? response.json() : Promise.reject()).then((payload) => {
      setState(payload); setNotice(payload.ready ? "Готово к запуску в одиночной игре или LAN." : "Проверьте путь к игре или сборку мода.");
    }).catch(() => setNotice("Предпросмотр активен. Для запуска игры откройте launcher.py."));
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
  async function launchGame() {
    stopSound();
    setLaunching(true); setNotice(`Запускаем Arma 3 с «${launcherName}»…`);
    try {
      const response = await fetch("/api/launch", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Не удалось запустить игру.");
      setNotice(payload.message);
    } catch (error) { setNotice(error.message || "Не удалось связаться с локальным лаунчером."); }
    finally { setLaunching(false); }
  }
  async function requestUpdate(action) {
    setUpdating(true);
    try {
      const response = await fetch(`/api/update/${action}`, { method: "POST" });
      const payload = await response.json();
      setUpdate(payload); setNotice(payload.message || "Статус обновления получен.");
    } catch (error) { setNotice("Не удалось связаться с модулем обновления."); }
    finally { setUpdating(false); }
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
  const mod = state.mods[0] || fallback.mods[0];
  const gameFound = state.game.exists && state.game.compatible;
  return <main className="app-shell"><section className="launcher" aria-label={`Лаунчер ${launcherName}`}>
    <audio ref={soundtrack} src="/assets/sanyok-soundtrack.mp3" autoPlay loop preload="auto" />
    <header className="hero"><img src="/assets/battlefield-dusk-hero.png" alt="Солдат с парашютом над побережьем на закате" />
      <div className="hero-brand"><div className="brand-kicker">ЛОКАЛЬНАЯ СБОРКА</div><div className="brand-name">ТЕРРИТОРИЯ<br />САНЬКА</div><div className="brand-subtitle">КОРОЛЕВСКАЯ БИТВА · ARMA 3 · OFFLINE</div></div>
      <button className={`sound-toggle ${soundMuted ? "muted" : ""}`} type="button" onClick={toggleSound} aria-label={soundMuted ? "Включить фоновую музыку" : "Выключить фоновую музыку"} title={soundMuted ? "Включить музыку" : "Выключить музыку"}><FontAwesomeIcon icon={soundMuted ? faVolumeXmark : faVolumeHigh} aria-hidden="true" /></button>
      <div className="hero-status"><FontAwesomeIcon icon={faSatelliteDish} aria-hidden="true" /><span>ОДИН МОД · БЕЗ КАРТ</span></div>
    </header>
    <div className="content-grid">
      <section className="panel game-panel" aria-label="Игра">
        <PanelTitle icon={faGamepad} detail={gameFound ? `v${state.game.version}` : "требуется v1.94"}>Игра</PanelTitle>
        <div className="game-row"><div className={`game-indicator ${gameFound ? "found" : "not-found"}`} aria-label={gameFound ? "Arma 3 найдена" : "Arma 3 не найдена"}><FontAwesomeIcon icon={gameFound ? faCheck : faTriangleExclamation} aria-hidden="true" /></div><div className="game-copy"><strong>Arma 3</strong><span>{gameFound ? `Найдена · ${state.game.source || "локальный кэш"}` : "Не найдена совместимая копия игры"}</span>{gameFound ? <code>{state.game.path}</code> : null}</div><div className={`availability ${gameFound ? "available" : "missing"}`}>{gameFound ? "Найдена" : "Не найдена"}</div></div>
        <form className="game-path-form" onSubmit={saveGamePath}><label htmlFor="game-dir"><FontAwesomeIcon icon={faFolderOpen} aria-hidden="true" />Папка с Arma 3</label><div><input id="game-dir" value={gameDir} onChange={(event) => setGameDir(event.target.value)} placeholder="Например: D:\\SteamLibrary\\steamapps\\common\\Arma 3" /><button type="submit" disabled={savingPath || !gameDir.trim()}>{savingPath ? "Проверяем…" : "Указать путь"}</button></div><p>При каждом открытии лаунчер проверяет сохранённую папку. Если игра перенесена — ищет её заново.</p></form>
      </section>
      <section className="panel mods-panel" aria-label="Моды"><PanelTitle icon={faPuzzlePiece} detail="(1)">Моды</PanelTitle>
        <article className="mod-row"><div className={`checkbox ${mod.exists ? "checked" : ""}`} aria-label={mod.exists ? "Мод найден" : "Мод не найден"}>{mod.exists ? <FontAwesomeIcon icon={faCheck} aria-hidden="true" /> : null}</div><div className="mod-mark"><FontAwesomeIcon icon={faSatelliteDish} aria-hidden="true" /></div><div className="mod-copy"><strong>{mod.name}</strong><span>{mod.description}</span></div><div className={`availability ${mod.exists ? "available" : "missing"}`}>{mod.exists ? "Готов" : "Не найден"}</div></article>
        <p className="panel-footnote"><FontAwesomeIcon icon={faCircleInfo} aria-hidden="true" />Мод подключается только из локальной собранной папки.</p>
      </section>
      <section className="panel maps-panel" aria-label="Карты"><PanelTitle icon={faMap} detail="(0)">Карты</PanelTitle><div className="empty-maps"><FontAwesomeIcon icon={faMap} aria-hidden="true" /><strong>Карты пока не подключены</strong><span>Поле намеренно оставлено пустым.</span></div></section>
    </div>
    <section className="update-area" aria-label="Обновления лаунчера"><div><strong>Обновления лаунчера</strong><span>{update?.latest_version ? `Версия ${update.latest_version}` : `Текущая версия ${state.launcher?.version || fallback.launcher.version}`}</span></div><div className="update-actions"><button type="button" onClick={() => requestUpdate("check")} disabled={updating}><FontAwesomeIcon icon={faArrowsRotate} aria-hidden="true" />{updating ? "Проверяем…" : "Проверить"}</button>{update?.available && !update?.staged ? <button type="button" onClick={() => requestUpdate("download")} disabled={updating}><FontAwesomeIcon icon={faDownload} aria-hidden="true" />Подготовить</button> : null}{update?.staged ? <button type="button" className="install-update" onClick={() => requestUpdate("install")} disabled={updating}><FontAwesomeIcon icon={faDownload} aria-hidden="true" />Установить и перезапустить</button> : null}</div></section>
    <footer className="launch-area"><p className="launch-status" role="status">{notice}</p><button className="launch-button" onClick={launchGame} disabled={launching || !state.ready}><FontAwesomeIcon icon={faPlay} aria-hidden="true" /><span>{launching ? "Запуск…" : "Играть"}</span></button><p className="launch-note">{gameFound ? `${state.game.name} · -world=empty` : "Укажите папку с Arma 3 1.94, чтобы продолжить"}</p></footer>
  </section></main>;
}
