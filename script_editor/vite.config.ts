import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import type { Plugin } from "vite";
import vue from "@vitejs/plugin-vue";

const projectDir = path.dirname(fileURLToPath(import.meta.url));
const customFabledDir = path.join(projectDir, "public", "custom", "fabled");
const customFabledIndexPath = path.join(customFabledDir, "index.json");
const databaseFabledDir = path.join(projectDir, "public", "characters", "fabled");
const databaseFabledIndexPath = path.join(databaseFabledDir, "index.json");
const customJinxDir = path.join(projectDir, "public", "custom", "jinxes");
const customJinxIndexPath = path.join(customJinxDir, "index.json");
const databaseJinxDir = path.join(projectDir, "public", "jinxes");
const databaseJinxIndexPath = path.join(databaseJinxDir, "index.json");
type FabledSource = "custom" | "database";
type CharacterSource = "custom" | "database";
type JinxSource = "custom" | "database";
type CharacterTeam = "townsfolk" | "outsider" | "minion" | "demon" | "traveler";

const characterFolders: Record<CharacterTeam, string> = {
  townsfolk: "townsfolks",
  outsider: "outsiders",
  minion: "minions",
  demon: "demons",
  traveler: "travelers",
};

function imageProxyPlugin(): Plugin {
  return {
    name: "botc-image-proxy",
    configureServer(server) {
      server.middlewares.use("/__image_proxy", async (request, response) => {
        try {
          const requestUrl = new URL(request.url ?? "", "http://127.0.0.1");
          const targetUrl = requestUrl.searchParams.get("url");
          if (!targetUrl || !/^https?:\/\//u.test(targetUrl)) {
            response.statusCode = 400;
            response.end("Missing or invalid image URL.");
            return;
          }

          const upstream = await fetch(targetUrl, {
            headers: {
              accept: "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
              referer: new URL(targetUrl).origin,
              "user-agent":
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
            },
          });
          if (!upstream.ok) {
            response.statusCode = upstream.status;
            response.end(`Image request failed: ${upstream.status}`);
            return;
          }

          const contentType = upstream.headers.get("content-type") ?? "application/octet-stream";
          if (!contentType.startsWith("image/")) {
            response.statusCode = 415;
            response.end("URL did not return an image.");
            return;
          }

          response.statusCode = 200;
          response.setHeader("content-type", contentType);
          response.setHeader("cache-control", "public, max-age=86400");
          response.end(Buffer.from(await upstream.arrayBuffer()));
        } catch (error) {
          response.statusCode = 502;
          response.end(error instanceof Error ? error.message : "Image proxy failed.");
        }
      });
    },
  };
}

function customFabledPlugin(): Plugin {
  return {
    name: "botc-custom-fabled",
    configureServer(server) {
      server.middlewares.use("/__custom_fabled", async (request, response) => {
        if (request.method !== "POST") {
          response.statusCode = 405;
          response.end("Method not allowed.");
          return;
        }

        try {
          const body = await readRequestJson(request);
          const record = isRecord(body.record) ? body.record : null;
          const name = cleanText(record?.name);
          if (!record || !name) {
            response.statusCode = 400;
            response.end("Missing fabled character record.");
            return;
          }

          const fileName = safeCustomFabledFileName(cleanText(body.fileName) || name);
          const incomingRecord = {
            ...record,
            id: cleanText(record.id) || name,
            name,
            team: "fabled",
            fileName,
            totalOccurrenceCount: Number(record.totalOccurrenceCount) || 1,
          };
          const nextRecord = incomingRecord;

          await mkdir(customFabledDir, { recursive: true });
          await writeFile(path.join(customFabledDir, fileName), `${JSON.stringify(nextRecord, null, 2)}\n`);
          const index = await readCustomFabledIndex();
          const nextItem = {
            id: cleanText(nextRecord.id) || name,
            name,
            team: "fabled",
            totalOccurrenceCount: Number(nextRecord.totalOccurrenceCount) || 1,
            fileName,
          };
          const existingIndex = index.characters.findIndex((item) => item.name === name);
          if (existingIndex >= 0) {
            index.characters[existingIndex] = nextItem;
          } else {
            index.characters.unshift(nextItem);
          }
          index.characterCount = index.characters.length;
          index.totalOccurrenceCount = index.characters.reduce(
            (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
            0,
          );
          await writeFile(customFabledIndexPath, `${JSON.stringify(index, null, 2)}\n`);

          response.statusCode = 200;
          response.setHeader("content-type", "application/json");
          response.end(JSON.stringify({ record: nextRecord, index }));
        } catch (error) {
          response.statusCode = 500;
          response.end(error instanceof Error ? error.message : "Failed to save custom fabled character.");
        }
      });

      server.middlewares.use("/__fabled_record", async (request, response) => {
        if (request.method === "POST") {
          try {
            const body = await readRequestJson(request);
            const source = body.source === "database" ? "database" : "custom";
            const record = isRecord(body.record) ? body.record : null;
            const name = cleanText(record?.name);
            if (!record || !name) {
              response.statusCode = 400;
              response.end("Missing fabled character record.");
              return;
            }

            const directory = fabledDirectory(source);
            const fileName = safeCustomFabledFileName(cleanText(body.fileName) || name);
            const nextRecord = {
              ...record,
              id: cleanText(record.id) || name,
              name,
              team: "fabled",
              fileName,
              totalOccurrenceCount: Number(record.totalOccurrenceCount) || 1,
            };

            await mkdir(directory, { recursive: true });
            await writeFile(path.join(directory, fileName), `${JSON.stringify(nextRecord, null, 2)}\n`);
            const indexPath = fabledIndexPath(source);
            const index = await readFabledIndex(indexPath);
            const nextItem = {
              id: cleanText(nextRecord.id) || name,
              name,
              team: "fabled",
              totalOccurrenceCount: Number(nextRecord.totalOccurrenceCount) || 1,
              fileName,
            };
            const existingIndex = index.characters.findIndex((item) => item.name === name || item.fileName === fileName);
            if (existingIndex >= 0) {
              index.characters[existingIndex] = nextItem;
            } else {
              index.characters.unshift(nextItem);
            }
            index.characterCount = index.characters.length;
            index.totalOccurrenceCount = index.characters.reduce(
              (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
              0,
            );
            await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

            response.statusCode = 200;
            response.setHeader("content-type", "application/json");
            response.end(JSON.stringify({ record: nextRecord, index }));
          } catch (error) {
            response.statusCode = 500;
            response.end(error instanceof Error ? error.message : "Failed to save fabled character.");
          }
          return;
        }

        if (request.method !== "DELETE") {
          response.statusCode = 405;
          response.end("Method not allowed.");
          return;
        }

        try {
          const body = await readRequestJson(request);
          const source = body.source === "database" ? "database" : "custom";
          const directory = fabledDirectory(source);
          const fileName = safeCustomFabledFileName(cleanText(body.fileName) || cleanText(body.name));
          const name = cleanText(body.name) || fileName.replace(/\.json$/u, "");
          await unlink(path.join(directory, fileName)).catch((error: NodeJS.ErrnoException) => {
            if (error.code !== "ENOENT") {
              throw error;
            }
          });

          const indexPath = fabledIndexPath(source);
          const index = await readFabledIndex(indexPath);
          index.characters = index.characters.filter((item) => item.name !== name && item.fileName !== fileName);
          index.characterCount = index.characters.length;
          index.totalOccurrenceCount = index.characters.reduce(
            (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
            0,
          );
          await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

          response.statusCode = 200;
          response.setHeader("content-type", "application/json");
          response.end(JSON.stringify({ ok: true, index }));
        } catch (error) {
          response.statusCode = 500;
          response.end(error instanceof Error ? error.message : "Failed to delete fabled character.");
        }
      });
    },
  };
}

function customCharacterPlugin(): Plugin {
  return {
    name: "botc-custom-character",
    configureServer(server) {
      server.middlewares.use("/__custom_character", async (request, response) => {
        if (request.method !== "POST") {
          response.statusCode = 405;
          response.end("Method not allowed.");
          return;
        }

        try {
          const body = await readRequestJson(request);
          const team = normalizeCharacterTeam(body.team);
          const record = isRecord(body.record) ? body.record : null;
          const name = cleanText(record?.name);
          if (!team || !record || !name) {
            response.statusCode = 400;
            response.end("Missing character team or record.");
            return;
          }

          const customDir = characterDirectory(team, "custom");
          const fileName = safeCustomCharacterFileName(cleanText(body.fileName) || name);
          const incomingRecord = {
            ...record,
            id: cleanText(record.id) || name,
            name,
            team,
            fileName,
            totalOccurrenceCount: Number(record.totalOccurrenceCount) || 1,
          };
          const nextRecord = incomingRecord;

          await mkdir(customDir, { recursive: true });
          await writeFile(path.join(customDir, fileName), `${JSON.stringify(nextRecord, null, 2)}\n`);
          const indexPath = characterIndexPath(team, "custom");
          const index = await readCharacterIndex(team, indexPath);
          const nextItem = {
            id: cleanText(nextRecord.id) || name,
            name,
            team,
            totalOccurrenceCount: Number(nextRecord.totalOccurrenceCount) || 1,
            fileName,
          };
          const existingIndex = index.characters.findIndex((item) => item.name === name);
          if (existingIndex >= 0) {
            index.characters[existingIndex] = nextItem;
          } else {
            index.characters.unshift(nextItem);
          }
          index.characterCount = index.characters.length;
          index.totalOccurrenceCount = index.characters.reduce(
            (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
            0,
          );
          await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

          response.statusCode = 200;
          response.setHeader("content-type", "application/json");
          response.end(JSON.stringify({ record: nextRecord, index }));
        } catch (error) {
          response.statusCode = 500;
          response.end(error instanceof Error ? error.message : "Failed to save custom character.");
        }
      });

      server.middlewares.use("/__character_record", async (request, response) => {
        if (request.method === "POST") {
          try {
            const body = await readRequestJson(request);
            const team = normalizeCharacterTeam(body.team);
            const source = body.source === "database" ? "database" : "custom";
            const record = isRecord(body.record) ? body.record : null;
            const name = cleanText(record?.name);
            if (!team || !record || !name) {
              response.statusCode = 400;
              response.end("Missing character team or record.");
              return;
            }

            const directory = characterDirectory(team, source);
            const fileName = safeCustomCharacterFileName(cleanText(body.fileName) || name);
            const nextRecord = {
              ...record,
              id: cleanText(record.id) || name,
              name,
              team,
              fileName,
              totalOccurrenceCount: Number(record.totalOccurrenceCount) || 1,
            };

            await mkdir(directory, { recursive: true });
            await writeFile(path.join(directory, fileName), `${JSON.stringify(nextRecord, null, 2)}\n`);
            const indexPath = characterIndexPath(team, source);
            const index = await readCharacterIndex(team, indexPath);
            const nextItem = {
              id: cleanText(nextRecord.id) || name,
              name,
              team,
              totalOccurrenceCount: Number(nextRecord.totalOccurrenceCount) || 1,
              fileName,
            };
            const existingIndex = index.characters.findIndex((item) => item.name === name || item.fileName === fileName);
            if (existingIndex >= 0) {
              index.characters[existingIndex] = nextItem;
            } else {
              index.characters.unshift(nextItem);
            }
            index.characterCount = index.characters.length;
            index.totalOccurrenceCount = index.characters.reduce(
              (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
              0,
            );
            await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

            response.statusCode = 200;
            response.setHeader("content-type", "application/json");
            response.end(JSON.stringify({ record: nextRecord, index }));
          } catch (error) {
            response.statusCode = 500;
            response.end(error instanceof Error ? error.message : "Failed to save character.");
          }
          return;
        }

        if (request.method !== "DELETE") {
          response.statusCode = 405;
          response.end("Method not allowed.");
          return;
        }

        try {
          const body = await readRequestJson(request);
          const team = normalizeCharacterTeam(body.team);
          const source = body.source === "database" ? "database" : "custom";
          if (!team) {
            response.statusCode = 400;
            response.end("Missing character team.");
            return;
          }

          const directory = characterDirectory(team, source);
          const fileName = safeCustomCharacterFileName(cleanText(body.fileName) || cleanText(body.name));
          const name = cleanText(body.name) || fileName.replace(/\.json$/u, "");
          await unlink(path.join(directory, fileName)).catch((error: NodeJS.ErrnoException) => {
            if (error.code !== "ENOENT") {
              throw error;
            }
          });

          const indexPath = characterIndexPath(team, source);
          const index = await readCharacterIndex(team, indexPath);
          index.characters = index.characters.filter((item) => item.name !== name && item.fileName !== fileName);
          index.characterCount = index.characters.length;
          index.totalOccurrenceCount = index.characters.reduce(
            (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
            0,
          );
          await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

          response.statusCode = 200;
          response.setHeader("content-type", "application/json");
          response.end(JSON.stringify({ ok: true, index }));
        } catch (error) {
          response.statusCode = 500;
          response.end(error instanceof Error ? error.message : "Failed to delete character.");
        }
      });
    },
  };
}

function customJinxPlugin(): Plugin {
  return {
    name: "botc-custom-jinx",
    configureServer(server) {
      server.middlewares.use("/__jinx_record", async (request, response) => {
        if (request.method === "DELETE") {
          try {
            const body = await readRequestJson(request);
            const source = body.source === "database" ? "database" : "custom";
            const directory = jinxDirectory(source);
            const fileName = safeCustomJinxFileName(cleanText(body.fileName) || cleanText(body.name));
            const name = cleanText(body.name) || fileName.replace(/\.json$/u, "");

            await unlink(path.join(directory, fileName)).catch((error: NodeJS.ErrnoException) => {
              if (error.code !== "ENOENT") {
                throw error;
              }
            });

            const indexPath = jinxIndexPath(source);
            const index = await readJinxIndex(indexPath);
            index.jinxes = index.jinxes.filter((item) => item.name !== name && item.fileName !== fileName);
            index.jinxCount = index.jinxes.length;
            index.totalOccurrenceCount = index.jinxes.reduce(
              (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
              0,
            );
            await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

            response.statusCode = 200;
            response.setHeader("content-type", "application/json");
            response.end(JSON.stringify({ ok: true, index }));
          } catch (error) {
            response.statusCode = 500;
            response.end(error instanceof Error ? error.message : "Failed to delete jinx.");
          }
          return;
        }

        if (request.method !== "POST") {
          response.statusCode = 405;
          response.end("Method not allowed.");
          return;
        }

        try {
          const body = await readRequestJson(request);
          const source = body.source === "database" ? "database" : "custom";
          const record = isRecord(body.record) ? body.record : null;
          const name = cleanText(record?.name);
          if (!record || !name) {
            response.statusCode = 400;
            response.end("Missing jinx record.");
            return;
          }

          const directory = jinxDirectory(source);
          const fileName = safeCustomJinxFileName(cleanText(body.fileName) || name);
          const nextRecord = sanitizeJinxRecord(record, name);

          await mkdir(directory, { recursive: true });
          await writeFile(path.join(directory, fileName), `${JSON.stringify(nextRecord, null, 2)}\n`);
          const indexPath = jinxIndexPath(source);
          const index = await readJinxIndex(indexPath);
          const nextItem = {
            id: cleanText(nextRecord.id) || name,
            name,
            team: "jinx",
            totalOccurrenceCount: Number(nextRecord.totalOccurrenceCount) || 1,
            fileName,
          };
          const existingIndex = index.jinxes.findIndex((item) => item.name === name || item.fileName === fileName);
          if (existingIndex >= 0) {
            index.jinxes[existingIndex] = nextItem;
          } else {
            index.jinxes.unshift(nextItem);
          }
          index.jinxCount = index.jinxes.length;
          index.totalOccurrenceCount = index.jinxes.reduce(
            (total, item) => total + (Number(item.totalOccurrenceCount) || 0),
            0,
          );
          await writeFile(indexPath, `${JSON.stringify(index, null, 2)}\n`);

          response.statusCode = 200;
          response.setHeader("content-type", "application/json");
          response.end(JSON.stringify({ record: nextRecord, index }));
        } catch (error) {
          response.statusCode = 500;
          response.end(error instanceof Error ? error.message : "Failed to save jinx.");
        }
      });
    },
  };
}

function fabledDirectory(source: FabledSource) {
  return source === "database" ? databaseFabledDir : customFabledDir;
}

function fabledIndexPath(source: FabledSource) {
  return source === "database" ? databaseFabledIndexPath : customFabledIndexPath;
}

function characterDirectory(team: CharacterTeam, source: CharacterSource) {
  return path.join(projectDir, "public", source === "database" ? "characters" : "custom", characterFolders[team]);
}

function characterIndexPath(team: CharacterTeam, source: CharacterSource) {
  return path.join(characterDirectory(team, source), "index.json");
}

function jinxDirectory(source: JinxSource) {
  return source === "database" ? databaseJinxDir : customJinxDir;
}

function jinxIndexPath(source: JinxSource) {
  return source === "database" ? databaseJinxIndexPath : customJinxIndexPath;
}

async function readCustomFabledIndex() {
  return readFabledIndex(customFabledIndexPath);
}

async function readFabledIndex(indexPath: string) {
  try {
    const parsed = JSON.parse(await readFile(indexPath, "utf8"));
    if (isRecord(parsed) && Array.isArray(parsed.characters)) {
      return {
        team: "fabled",
        folder: "fabled",
        characterCount: Number(parsed.characterCount) || parsed.characters.length,
        totalOccurrenceCount: Number(parsed.totalOccurrenceCount) || 0,
        characters: parsed.characters.filter(isRecord).map((item) => ({
          id: cleanText(item.id) || cleanText(item.name),
          name: cleanText(item.name) || cleanText(item.id),
          team: "fabled",
          totalOccurrenceCount: Number(item.totalOccurrenceCount) || 1,
          fileName: cleanText(item.fileName),
        })),
      };
    }
  } catch {
    // Missing custom index means the user has not saved custom fabled characters yet.
  }

  return {
    team: "fabled",
    folder: "fabled",
    characterCount: 0,
    totalOccurrenceCount: 0,
    characters: [],
  };
}

async function readCharacterIndex(team: CharacterTeam, indexPath: string) {
  try {
    const parsed = JSON.parse(await readFile(indexPath, "utf8"));
    if (isRecord(parsed) && Array.isArray(parsed.characters)) {
      return {
        team,
        folder: characterFolders[team],
        characterCount: Number(parsed.characterCount) || parsed.characters.length,
        totalOccurrenceCount: Number(parsed.totalOccurrenceCount) || 0,
        characters: parsed.characters.filter(isRecord).map((item) => ({
          id: cleanText(item.id) || cleanText(item.name),
          name: cleanText(item.name) || cleanText(item.id),
          team,
          totalOccurrenceCount: Number(item.totalOccurrenceCount) || 1,
          fileName: cleanText(item.fileName),
        })),
      };
    }
  } catch {
    // Missing custom index means the user has not saved custom characters yet.
  }

  return {
    team,
    folder: characterFolders[team],
    characterCount: 0,
    totalOccurrenceCount: 0,
    characters: [],
  };
}

async function readJinxIndex(indexPath: string) {
  try {
    const parsed = JSON.parse(await readFile(indexPath, "utf8"));
    if (isRecord(parsed) && Array.isArray(parsed.jinxes)) {
      return {
        source: cleanText(parsed.source) || "jinxes",
        jinxCount: Number(parsed.jinxCount) || parsed.jinxes.length,
        totalOccurrenceCount: Number(parsed.totalOccurrenceCount) || 0,
        jinxes: parsed.jinxes.filter(isRecord).map((item) => ({
          id: cleanText(item.id) || cleanText(item.name),
          name: cleanText(item.name) || cleanText(item.id),
          team: "jinx",
          totalOccurrenceCount: Number(item.totalOccurrenceCount) || 1,
          fileName: cleanText(item.fileName),
        })),
      };
    }
  } catch {
    // Missing custom index means the user has not saved custom jinxes yet.
  }

  return {
    source: "custom_jinxes",
    jinxCount: 0,
    totalOccurrenceCount: 0,
    jinxes: [],
  };
}

function sanitizeJinxRecord(record: Record<string, unknown>, name: string) {
  const variants = isRecord(record.variants) ? record.variants : {};
  return {
    id: cleanText(record.id) || name,
    name,
    team: "jinx",
    targets: toStringArray(record.targets),
    targetDetectionNotes: toStringArray(record.targetDetectionNotes),
    issueNotes: toStringArray(record.issueNotes),
    totalOccurrenceCount: Number(record.totalOccurrenceCount) || 1,
    variants: {
      ability: toStringVariants(variants.ability ?? record.ability),
    },
  };
}

async function readRequestJson(request: import("node:http").IncomingMessage) {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function safeCustomFabledFileName(value: string) {
  const withoutExtension = value.endsWith(".json") ? value.slice(0, -5) : value;
  return `${withoutExtension.trim().replace(/[\\/:*?"<>|]+/g, "_") || "未命名传奇角色"}.json`;
}

function safeCustomCharacterFileName(value: string) {
  const withoutExtension = value.endsWith(".json") ? value.slice(0, -5) : value;
  return `${withoutExtension.trim().replace(/[\\/:*?"<>|]+/g, "_") || "未命名角色"}.json`;
}

function safeCustomJinxFileName(value: string) {
  const withoutExtension = value.endsWith(".json") ? value.slice(0, -5) : value;
  return `${withoutExtension.trim().replace(/\s+/gu, "_").replace(/[\\/:*?"<>|]+/g, "_") || "未命名相克规则"}.json`;
}

function normalizeCharacterTeam(value: unknown): CharacterTeam | null {
  const team = cleanText(value);
  return team in characterFolders ? team as CharacterTeam : null;
}

function cleanText(value: unknown) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function toStringArray(value: unknown) {
  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean);
  }
  return cleanText(value)
    .split("||")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toStringVariants(value: unknown) {
  const values = Array.isArray(value) ? value.map(cleanText) : [cleanText(value)];
  const filtered = values.filter((item, index) => item || index === 0);
  return filtered.length ? filtered : [""];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export default defineConfig({
  plugins: [vue(), imageProxyPlugin(), customFabledPlugin(), customCharacterPlugin(), customJinxPlugin()],
  clearScreen: false,
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true,
  },
});
