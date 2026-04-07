/**
 * 锤子便签 Markdown 导出 - 浏览器控制台独立脚本
 *
 * 使用方法：
 * 1. 打开 https://cloud.smartisan.com 并登录
 * 2. 等待笔记同步完成
 * 3. 打开浏览器开发者工具（F12）-> Console
 * 4. 复制粘贴本脚本并回车执行
 */

(async function () {
  "use strict";

  // ---- 加载依赖 ----
  async function loadScript(url) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = url;
      s.onload = resolve;
      s.onerror = () => reject(new Error("加载失败: " + url));
      document.head.appendChild(s);
    });
  }

  if (typeof JSZip === "undefined") {
    console.log("[导出] 加载 JSZip...");
    await loadScript("https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js");
  }
  if (typeof saveAs === "undefined") {
    console.log("[导出] 加载 FileSaver...");
    await loadScript("https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js");
  }

  // ---- IndexedDB 读取 ----
  function openDB(name) {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(name);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(new Error("无法打开数据库: " + name));
    });
  }

  function readAll(db, store) {
    return new Promise((resolve, reject) => {
      try {
        const tx = db.transaction(store, "readonly");
        const req = tx.objectStore(store).getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      } catch (e) {
        reject(e);
      }
    });
  }

  // ---- 列出所有 IndexedDB 数据库（调试用） ----
  if (indexedDB.databases) {
    const dbs = await indexedDB.databases();
    console.log("[导出] 可用的 IndexedDB 数据库:", dbs.map((d) => d.name));
  }

  // ---- 读取数据 ----
  const dbConfigs = [
    { dbNames: ["_pouch_folder", "_pouch_folders"], type: "folder" },
    { dbNames: ["_pouch_note", "_pouch_notes"], type: "note" },
  ];
  const storeNames = ["by-sequence", "docs", "local-store"];

  const result = { folder: [], note: [] };

  for (const config of dbConfigs) {
    for (const dbName of config.dbNames) {
      if (result[config.type].length > 0) break;
      try {
        const db = await openDB(dbName);
        const stores = Array.from(db.objectStoreNames);
        console.log(`[导出] 数据库 ${dbName} 的 stores:`, stores);

        for (const store of storeNames) {
          if (!stores.includes(store)) continue;
          try {
            const records = await readAll(db, store);
            if (records.length > 0) {
              result[config.type] = records;
              console.log(`[导出] ${config.type} 数据: ${dbName}/${store}, ${records.length} 条`);
              break;
            }
          } catch (_) {}
        }
        db.close();
      } catch (_) {}
    }
  }

  if (result.note.length === 0) {
    console.error("[导出] 未找到笔记数据！请确保：");
    console.error("  1. 已登录 cloud.smartisan.com");
    console.error("  2. 笔记已同步到本地");
    console.error("  3. 在正确的域名下运行本脚本");
    return;
  }

  // ---- 解析文件夹 ----
  const folderMap = new Map();
  for (const item of result.folder) {
    if (item._deleted) continue;
    const f = item.folder || item.data || item;
    const id = f.sync_id || f.syncId || f._id || f.id;
    const title = f.title || f.name || "未命名文件夹";
    if (id) folderMap.set(id, title);
  }
  console.log(`[导出] 文件夹: ${folderMap.size} 个`);

  // ---- 解析笔记 ----
  const notes = [];
  for (const item of result.note) {
    if (item._deleted) continue;
    const n = item.note || item.data || item;
    if (!n || (!n.detail && !n.content && !n.body)) continue;

    const title = (n.title || n._id || "无标题").replace(/[\\/:*?"<>|\n\r]/g, "_").trim() || "无标题";
    const detail = n.detail || n.content || n.body || "";
    const folderId = n.folderId || n.folder_id || n.categoryId || "";
    const modifyTime = new Date(n.modify_time || n.modifyTime || n.updated_at || Date.now());
    const folderName = folderMap.get(folderId) || "未分类";

    notes.push({ title, detail, folderName, modifyTime });
  }
  console.log(`[导出] 笔记: ${notes.length} 条`);

  if (notes.length === 0) {
    console.error("[导出] 没有可导出的笔记");
    return;
  }

  // ---- 打包 ZIP ----
  const zip = new JSZip();
  const groups = new Map();
  for (const note of notes) {
    if (!groups.has(note.folderName)) groups.set(note.folderName, []);
    groups.get(note.folderName).push(note);
  }

  for (const [folderName, folderNotes] of groups) {
    const folder = zip.folder(folderName);
    const usedNames = new Map();

    for (const note of folderNotes) {
      let filename = note.title;
      const count = usedNames.get(filename) || 0;
      usedNames.set(filename, count + 1);
      if (count > 0) filename = `${filename}_${count}`;

      const timeStr = note.modifyTime.toLocaleString("zh-CN", {
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });

      folder.file(`${filename}.md`, `# ${filename}\n\n> 修改时间：${timeStr}\n\n${note.detail}\n`);
    }
  }

  const blob = await zip.generateAsync({ type: "blob" });
  const ts = new Date().toISOString().slice(0, 10);
  saveAs(blob, `smartisan-notes-${ts}.zip`);

  console.log(`[导出] 完成！共导出 ${notes.length} 条笔记，${groups.size} 个文件夹`);
})();
