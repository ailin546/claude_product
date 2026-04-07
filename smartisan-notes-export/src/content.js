/**
 * 锤子便签 Markdown 导出工具
 *
 * 从浏览器 IndexedDB 中读取锤子便签数据（PouchDB 格式），
 * 将所有笔记导出为 Markdown 文件并打包为 ZIP 下载。
 *
 * 兼容 cloud.smartisan.com 和 note.smartisan.com
 */

// ============================================================
// JSZip 和 FileSaver 通过 CDN 动态加载（避免打包依赖）
// ============================================================

function loadScript(url) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = url;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`Failed to load script: ${url}`));
    document.head.appendChild(script);
  });
}

async function ensureDependencies() {
  if (typeof JSZip === "undefined") {
    await loadScript(
      "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"
    );
  }
  if (typeof saveAs === "undefined") {
    await loadScript(
      "https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js"
    );
  }
}

// ============================================================
// IndexedDB 读取
// ============================================================

function openDB(name) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(new Error(`Cannot open database: ${name}`));
  });
}

function readAllFromStore(db, storeName) {
  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(storeName, "readonly");
      const store = tx.objectStore(storeName);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(new Error(`Failed to read store: ${storeName}`));
    } catch (e) {
      reject(new Error(`Store "${storeName}" not found in database "${db.name}"`));
    }
  });
}

/**
 * 尝试多种已知的数据库名称和 object store 名称
 * 以兼容锤子便签不同版本的数据结构
 */
async function discoverDatabases() {
  const folderDBNames = ["_pouch_folder", "_pouch_folders"];
  const noteDBNames = ["_pouch_note", "_pouch_notes"];
  const storeNames = ["by-sequence", "docs", "local-store"];

  let folderRecords = [];
  let noteRecords = [];

  // 尝试读取文件夹数据
  for (const dbName of folderDBNames) {
    if (folderRecords.length > 0) break;
    try {
      const db = await openDB(dbName);
      for (const store of storeNames) {
        try {
          const records = await readAllFromStore(db, store);
          if (records.length > 0) {
            folderRecords = records;
            console.log(`[导出] 文件夹数据来源: ${dbName}/${store}, 共 ${records.length} 条`);
            break;
          }
        } catch (_) {
          // try next store
        }
      }
      db.close();
    } catch (_) {
      // try next db
    }
  }

  // 尝试读取笔记数据
  for (const dbName of noteDBNames) {
    if (noteRecords.length > 0) break;
    try {
      const db = await openDB(dbName);
      for (const store of storeNames) {
        try {
          const records = await readAllFromStore(db, store);
          if (records.length > 0) {
            noteRecords = records;
            console.log(`[导出] 笔记数据来源: ${dbName}/${store}, 共 ${records.length} 条`);
            break;
          }
        } catch (_) {
          // try next store
        }
      }
      db.close();
    } catch (_) {
      // try next db
    }
  }

  return { folderRecords, noteRecords };
}

// ============================================================
// 数据解析
// ============================================================

function parseFolders(records) {
  const folderMap = new Map();
  for (const item of records) {
    if (item._deleted) continue;

    // 兼容多种数据结构
    const folder = item.folder || item.data || item;
    const syncId = folder.sync_id || folder.syncId || folder._id || folder.id;
    const title = folder.title || folder.name || "未命名文件夹";

    if (syncId) {
      folderMap.set(syncId, title);
    }
  }
  return folderMap;
}

function parseNotes(records, folderMap) {
  const notes = [];
  for (const item of records) {
    if (item._deleted) continue;

    // 兼容多种数据结构
    const note = item.note || item.data || item;
    if (!note || (!note.detail && !note.content && !note.body)) continue;

    const title = note.title || note._id || note.id || "无标题";
    const detail = note.detail || note.content || note.body || "";
    const folderId = note.folderId || note.folder_id || note.categoryId || "";
    const modifyTime = note.modify_time || note.modifyTime || note.updated_at || note.updateTime || Date.now();

    const folderName = folderMap.get(folderId) || "未分类";

    notes.push({
      title: sanitizeFilename(title),
      detail,
      folderName,
      modifyTime: new Date(modifyTime),
    });
  }
  return notes;
}

function sanitizeFilename(name) {
  return name.replace(/[\\/:*?"<>|\n\r]/g, "_").trim() || "无标题";
}

function formatDate(date) {
  try {
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return date.toString();
  }
}

// ============================================================
// Markdown 生成与打包
// ============================================================

function noteToMarkdown(note) {
  const lines = [];
  lines.push(`# ${note.title}`);
  lines.push("");
  lines.push(`> 修改时间：${formatDate(note.modifyTime)}`);
  lines.push("");
  lines.push(note.detail);
  lines.push("");
  return lines.join("\n");
}

async function exportToZip(notes) {
  await ensureDependencies();

  const zip = new JSZip();

  // 按文件夹分组
  const groups = new Map();
  for (const note of notes) {
    if (!groups.has(note.folderName)) {
      groups.set(note.folderName, []);
    }
    groups.get(note.folderName).push(note);
  }

  // 处理文件名重复
  for (const [folderName, folderNotes] of groups) {
    const folder = zip.folder(folderName);
    const usedNames = new Map();

    for (const note of folderNotes) {
      let filename = note.title;
      const count = usedNames.get(filename) || 0;
      usedNames.set(filename, count + 1);
      if (count > 0) {
        filename = `${filename}_${count}`;
      }

      const markdown = noteToMarkdown(note);
      folder.file(`${filename}.md`, markdown);
    }
  }

  const blob = await zip.generateAsync({ type: "blob" });
  const timestamp = new Date().toISOString().slice(0, 10);
  saveAs(blob, `smartisan-notes-${timestamp}.zip`);

  return { folderCount: groups.size, noteCount: notes.length };
}

// ============================================================
// UI
// ============================================================

function showToast(message, duration) {
  const existing = document.querySelector(".smartisan-export-toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "smartisan-export-toast";
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add("show"));

  if (duration > 0) {
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  return toast;
}

function createExportButton() {
  const existing = document.querySelector(".smartisan-export-btn");
  if (existing) return;

  const btn = document.createElement("button");
  btn.className = "smartisan-export-btn";
  btn.textContent = "导出 Markdown";
  btn.addEventListener("click", handleExport);
  document.body.appendChild(btn);
}

async function handleExport() {
  const btn = document.querySelector(".smartisan-export-btn");
  if (!btn) return;

  btn.disabled = true;
  btn.textContent = "导出中...";
  const toast = showToast("正在读取笔记数据...", 0);

  try {
    const { folderRecords, noteRecords } = await discoverDatabases();

    if (noteRecords.length === 0) {
      showToast("未找到笔记数据，请确保已登录并同步笔记", 5000);
      return;
    }

    const folderMap = parseFolders(folderRecords);
    const notes = parseNotes(noteRecords, folderMap);

    if (notes.length === 0) {
      showToast("没有可导出的笔记", 5000);
      return;
    }

    toast.textContent = `正在打包 ${notes.length} 条笔记...`;

    const result = await exportToZip(notes);
    showToast(
      `导出完成！共 ${result.noteCount} 条笔记，${result.folderCount} 个文件夹`,
      5000
    );
  } catch (err) {
    console.error("[锤子便签导出] 错误:", err);
    showToast(`导出失败: ${err.message}`, 8000);
  } finally {
    btn.disabled = false;
    btn.textContent = "导出 Markdown";
    if (toast.parentNode) {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }
  }
}

// ============================================================
// 启动
// ============================================================

createExportButton();
console.log("[锤子便签导出] 插件已加载，点击右上角按钮导出笔记");
