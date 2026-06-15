use base64::{engine::general_purpose::STANDARD, Engine as _};
use reqwest::header::{ACCEPT, CONTENT_TYPE, REFERER, USER_AGENT};
use serde_json::{json, Value};
use std::{
  collections::HashSet,
  env,
  fs,
  path::{Path, PathBuf},
};

#[tauri::command]
async fn fetch_image_data_url(url: String) -> Result<String, String> {
  if !url.starts_with("http://") && !url.starts_with("https://") {
    return Err("Only http and https image URLs are supported.".to_string());
  }

  let parsed_url = reqwest::Url::parse(&url).map_err(|error| format!("Invalid image URL: {error}"))?;
  let referer = parsed_url
    .origin()
    .ascii_serialization();
  let client = reqwest::Client::new();
  let response = client
    .get(parsed_url)
    .header(ACCEPT, "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8")
    .header(REFERER, referer)
    .header(
      USER_AGENT,
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
    )
    .send()
    .await
    .map_err(|error| format!("Image request failed: {error}"))?;
  let status = response.status();
  if !status.is_success() {
    return Err(format!("Image request failed with status {status}."));
  }

  let content_type = response
    .headers()
    .get(CONTENT_TYPE)
    .and_then(|value| value.to_str().ok())
    .unwrap_or("application/octet-stream")
    .to_string();
  if !content_type.starts_with("image/") {
    return Err("URL did not return an image.".to_string());
  }

  let bytes = response
    .bytes()
    .await
    .map_err(|error| format!("Failed to read image response: {error}"))?;

  Ok(format!("data:{content_type};base64,{}", STANDARD.encode(bytes)))
}

#[tauri::command]
fn save_custom_fabled_character(file_name: Option<String>, record_json: String) -> Result<Value, String> {
  let mut record: Value = serde_json::from_str(&record_json)
    .map_err(|error| format!("Invalid fabled character JSON: {error}"))?;
  let name = json_text(record.get("name"));
  if name.is_empty() {
    return Err("Missing fabled character name.".to_string());
  }

  let file_name = safe_custom_fabled_file_name(file_name.as_deref().unwrap_or(&name));
  let directories = fabled_dirs("custom", true)?;
  let primary_directory = directories
    .first()
    .ok_or_else(|| "Failed to locate custom fabled folder.".to_string())?;
  for directory in &directories {
    fs::create_dir_all(directory).map_err(|error| format!("Failed to create custom fabled folder: {error}"))?;
  }

  if let Value::Object(map) = &mut record {
    let id = non_empty_text(json_text(map.get("id")), &name);
    map.insert("id".to_string(), Value::String(id));
    map.insert("name".to_string(), Value::String(name.clone()));
    map.insert("team".to_string(), Value::String("fabled".to_string()));
    map.insert("fileName".to_string(), Value::String(file_name.clone()));
    if !map.contains_key("totalOccurrenceCount") {
      map.insert("totalOccurrenceCount".to_string(), Value::Number(1.into()));
    }
  }

  for directory in &directories {
    write_fabled_record(directory, &file_name, &record)?;
    upsert_fabled_index_item(directory, &record, &file_name)?;
  }

  let primary_record = read_fabled_record(&primary_directory.join(&file_name)).unwrap_or(record);
  Ok(primary_record)
}

#[tauri::command]
fn delete_fabled_character(source: String, file_name: Option<String>, name: String) -> Result<(), String> {
  let file_name = safe_custom_fabled_file_name(file_name.as_deref().unwrap_or(&name));
  let name = if name.trim().is_empty() {
    file_name.trim_end_matches(".json").to_string()
  } else {
    name
  };
  let directories = fabled_dirs(&source, false)?;
  let mut deleted_anywhere = false;
  let mut removed_from_index = false;

  for directory in &directories {
    match fs::remove_file(directory.join(&file_name)) {
      Ok(()) => {
        deleted_anywhere = true;
      }
      Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
      Err(error) => return Err(format!("Failed to delete fabled character: {error}")),
    }
    removed_from_index = remove_fabled_index_item(directory, &file_name, &name)? || removed_from_index;
  }

  if deleted_anywhere || removed_from_index {
    Ok(())
  } else {
    Err(format!(
      "没有找到可删除的传奇角色文件或索引项：{name} ({file_name})。已检查 {} 个目录。",
      directories.len(),
    ))
  }
}

#[tauri::command]
fn save_custom_character(team: String, file_name: Option<String>, record_json: String) -> Result<Value, String> {
  let team = normalize_character_team(&team)?;
  let mut record: Value = serde_json::from_str(&record_json)
    .map_err(|error| format!("Invalid character JSON: {error}"))?;
  let name = json_text(record.get("name"));
  if name.is_empty() {
    return Err("Missing character name.".to_string());
  }

  let file_name = safe_custom_character_file_name(file_name.as_deref().unwrap_or(&name));
  let directories = character_dirs(&team, "custom", true)?;
  let primary_directory = directories
    .first()
    .ok_or_else(|| "Failed to locate custom character folder.".to_string())?;
  for directory in &directories {
    fs::create_dir_all(directory).map_err(|error| format!("Failed to create custom character folder: {error}"))?;
  }

  if let Value::Object(map) = &mut record {
    let id = non_empty_text(json_text(map.get("id")), &name);
    map.insert("id".to_string(), Value::String(id));
    map.insert("name".to_string(), Value::String(name.clone()));
    map.insert("team".to_string(), Value::String(team.clone()));
    map.insert("fileName".to_string(), Value::String(file_name.clone()));
    if !map.contains_key("totalOccurrenceCount") {
      map.insert("totalOccurrenceCount".to_string(), Value::Number(1.into()));
    }
  }

  for directory in &directories {
    write_character_record(directory, &file_name, &record)?;
    upsert_character_index_item(directory, &team, &record, &file_name)?;
  }

  let primary_record = read_character_record(&primary_directory.join(&file_name)).unwrap_or(record);
  Ok(primary_record)
}

#[tauri::command]
fn delete_character(team: String, source: String, file_name: Option<String>, name: String) -> Result<(), String> {
  let team = normalize_character_team(&team)?;
  let file_name = safe_custom_character_file_name(file_name.as_deref().unwrap_or(&name));
  let name = if name.trim().is_empty() {
    file_name.trim_end_matches(".json").to_string()
  } else {
    name
  };
  let directories = character_dirs(&team, &source, false)?;
  let mut deleted_anywhere = false;
  let mut removed_from_index = false;

  for directory in &directories {
    match fs::remove_file(directory.join(&file_name)) {
      Ok(()) => {
        deleted_anywhere = true;
      }
      Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
      Err(error) => return Err(format!("Failed to delete character: {error}")),
    }
    removed_from_index = remove_character_index_item(directory, &team, &file_name, &name)? || removed_from_index;
  }

  if deleted_anywhere || removed_from_index {
    Ok(())
  } else {
    Err(format!(
      "没有找到可删除的角色文件或索引项：{name} ({file_name})。已检查 {} 个目录。",
      directories.len(),
    ))
  }
}

fn write_fabled_record(directory: &Path, file_name: &str, record: &Value) -> Result<(), String> {
  let record_text = serde_json::to_string_pretty(record)
    .map_err(|error| format!("Failed to serialize fabled character: {error}"))?;
  fs::write(directory.join(file_name), format!("{record_text}\n"))
    .map_err(|error| format!("Failed to write fabled character: {error}"))
}

fn write_character_record(directory: &Path, file_name: &str, record: &Value) -> Result<(), String> {
  let record_text = serde_json::to_string_pretty(record)
    .map_err(|error| format!("Failed to serialize character: {error}"))?;
  fs::write(directory.join(file_name), format!("{record_text}\n"))
    .map_err(|error| format!("Failed to write character: {error}"))
}

fn upsert_fabled_index_item(directory: &Path, record: &Value, file_name: &str) -> Result<(), String> {
  let name = json_text(record.get("name"));
  let item_id = non_empty_text(json_text(record.get("id")), &name);
  let item = json!({
    "id": item_id,
    "name": name,
    "team": "fabled",
    "totalOccurrenceCount": record.get("totalOccurrenceCount").and_then(Value::as_u64).unwrap_or(1),
    "fileName": file_name
  });
  let mut index = read_fabled_index(directory);
  let (character_count, total_occurrence_count) = {
    let characters = index
      .get_mut("characters")
      .and_then(Value::as_array_mut)
      .ok_or_else(|| "Invalid fabled index.".to_string())?;
    if let Some(existing_index) = characters
      .iter()
      .position(|character| json_text(character.get("name")) == json_text(item.get("name")))
    {
      characters[existing_index] = item;
    } else {
      characters.insert(0, item);
    }
    let total_occurrence_count: u64 = characters
      .iter()
      .map(|character| character.get("totalOccurrenceCount").and_then(Value::as_u64).unwrap_or(0))
      .sum();
    (characters.len() as u64, total_occurrence_count)
  };
  index["characterCount"] = Value::Number(character_count.into());
  index["totalOccurrenceCount"] = Value::Number(total_occurrence_count.into());

  write_fabled_index(directory, &index)
}

fn remove_fabled_index_item(directory: &Path, file_name: &str, name: &str) -> Result<bool, String> {
  let mut index = read_fabled_index(directory);
  let original_count = index
    .get("characters")
    .and_then(Value::as_array)
    .map(Vec::len)
    .unwrap_or(0);
  let (character_count, total_occurrence_count) = {
    let characters = index
      .get_mut("characters")
      .and_then(Value::as_array_mut)
      .ok_or_else(|| "Invalid fabled index.".to_string())?;
    characters.retain(|character| {
      json_text(character.get("name")) != name && json_text(character.get("fileName")) != file_name
    });
    let total_occurrence_count: u64 = characters
      .iter()
      .map(|character| character.get("totalOccurrenceCount").and_then(Value::as_u64).unwrap_or(0))
      .sum();
    (characters.len() as u64, total_occurrence_count)
  };
  index["characterCount"] = Value::Number(character_count.into());
  index["totalOccurrenceCount"] = Value::Number(total_occurrence_count.into());

  write_fabled_index(directory, &index)?;
  Ok(character_count != original_count as u64)
}

fn upsert_character_index_item(directory: &Path, team: &str, record: &Value, file_name: &str) -> Result<(), String> {
  let name = json_text(record.get("name"));
  let item_id = non_empty_text(json_text(record.get("id")), &name);
  let item = json!({
    "id": item_id,
    "name": name,
    "team": team,
    "totalOccurrenceCount": record.get("totalOccurrenceCount").and_then(Value::as_u64).unwrap_or(1),
    "fileName": file_name
  });
  let mut index = read_character_index(directory, team);
  let (character_count, total_occurrence_count) = {
    let characters = index
      .get_mut("characters")
      .and_then(Value::as_array_mut)
      .ok_or_else(|| "Invalid character index.".to_string())?;
    if let Some(existing_index) = characters
      .iter()
      .position(|character| json_text(character.get("name")) == json_text(item.get("name")))
    {
      characters[existing_index] = item;
    } else {
      characters.insert(0, item);
    }
    let total_occurrence_count: u64 = characters
      .iter()
      .map(|character| character.get("totalOccurrenceCount").and_then(Value::as_u64).unwrap_or(0))
      .sum();
    (characters.len() as u64, total_occurrence_count)
  };
  index["characterCount"] = Value::Number(character_count.into());
  index["totalOccurrenceCount"] = Value::Number(total_occurrence_count.into());

  write_character_index(directory, &index)
}

fn remove_character_index_item(directory: &Path, team: &str, file_name: &str, name: &str) -> Result<bool, String> {
  let mut index = read_character_index(directory, team);
  let original_count = index
    .get("characters")
    .and_then(Value::as_array)
    .map(Vec::len)
    .unwrap_or(0);
  let (character_count, total_occurrence_count) = {
    let characters = index
      .get_mut("characters")
      .and_then(Value::as_array_mut)
      .ok_or_else(|| "Invalid character index.".to_string())?;
    characters.retain(|character| {
      json_text(character.get("name")) != name && json_text(character.get("fileName")) != file_name
    });
    let total_occurrence_count: u64 = characters
      .iter()
      .map(|character| character.get("totalOccurrenceCount").and_then(Value::as_u64).unwrap_or(0))
      .sum();
    (characters.len() as u64, total_occurrence_count)
  };
  index["characterCount"] = Value::Number(character_count.into());
  index["totalOccurrenceCount"] = Value::Number(total_occurrence_count.into());

  write_character_index(directory, &index)?;
  Ok(character_count != original_count as u64)
}

fn write_fabled_index(directory: &Path, index: &Value) -> Result<(), String> {
  let index_text = serde_json::to_string_pretty(&index)
    .map_err(|error| format!("Failed to serialize fabled index: {error}"))?;
  fs::write(directory.join("index.json"), format!("{index_text}\n"))
    .map_err(|error| format!("Failed to write fabled index: {error}"))
}

fn write_character_index(directory: &Path, index: &Value) -> Result<(), String> {
  let index_text = serde_json::to_string_pretty(&index)
    .map_err(|error| format!("Failed to serialize character index: {error}"))?;
  fs::write(directory.join("index.json"), format!("{index_text}\n"))
    .map_err(|error| format!("Failed to write character index: {error}"))
}

fn fabled_dirs(source: &str, allow_missing: bool) -> Result<Vec<PathBuf>, String> {
  let path_segment = if source == "database" {
    "characters/fabled"
  } else {
    "custom/fabled"
  };
  let mut directories = Vec::new();
  let mut seen = HashSet::new();

  for root in candidate_project_roots() {
    for asset_folder in ["public", "dist"] {
      let asset_root = root.join(asset_folder);
      let candidate = asset_root.join(path_segment);
      let usable = candidate.exists() || (allow_missing && asset_root.exists());
      if usable {
        push_unique_path(&mut directories, &mut seen, candidate);
      }
    }
  }

  if directories.is_empty() {
    Err(format!("Failed to locate fabled {source} database folders."))
  } else {
    Ok(directories)
  }
}

fn character_dirs(team: &str, source: &str, allow_missing: bool) -> Result<Vec<PathBuf>, String> {
  let folder = character_folder(team)?;
  let path_segment = if source == "database" {
    format!("characters/{folder}")
  } else {
    format!("custom/{folder}")
  };
  let mut directories = Vec::new();
  let mut seen = HashSet::new();

  for root in candidate_project_roots() {
    for asset_folder in ["public", "dist"] {
      let asset_root = root.join(asset_folder);
      let candidate = asset_root.join(&path_segment);
      let usable = candidate.exists() || (allow_missing && asset_root.exists());
      if usable {
        push_unique_path(&mut directories, &mut seen, candidate);
      }
    }
  }

  if directories.is_empty() {
    Err(format!("Failed to locate {team} {source} database folders."))
  } else {
    Ok(directories)
  }
}

fn candidate_project_roots() -> Vec<PathBuf> {
  let mut roots = Vec::new();
  let mut seen = HashSet::new();
  add_project_root_candidates(
    &mut roots,
    &mut seen,
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".."),
  );
  if let Ok(current_dir) = env::current_dir() {
    add_project_root_candidates(&mut roots, &mut seen, current_dir);
  }
  if let Ok(current_exe) = env::current_exe() {
    let start = current_exe
      .parent()
      .map(Path::to_path_buf)
      .unwrap_or(current_exe);
    add_project_root_candidates(&mut roots, &mut seen, start);
  }
  roots
}

fn add_project_root_candidates(roots: &mut Vec<PathBuf>, seen: &mut HashSet<String>, start: PathBuf) {
  for ancestor in start.ancestors().take(10) {
    push_unique_path(roots, seen, ancestor.to_path_buf());
    push_unique_path(roots, seen, ancestor.join("script_editor"));
  }
}

fn push_unique_path(paths: &mut Vec<PathBuf>, seen: &mut HashSet<String>, path: PathBuf) {
  let key = path.to_string_lossy().to_string();
  if seen.insert(key) {
    paths.push(path);
  }
}

fn read_fabled_record(path: &PathBuf) -> Option<Value> {
  fs::read_to_string(path)
    .ok()
    .and_then(|text| serde_json::from_str::<Value>(&text).ok())
    .filter(Value::is_object)
}

fn read_character_record(path: &PathBuf) -> Option<Value> {
  fs::read_to_string(path)
    .ok()
    .and_then(|text| serde_json::from_str::<Value>(&text).ok())
    .filter(Value::is_object)
}

fn read_fabled_index(directory: &Path) -> Value {
  let path = directory.join("index.json");
  let parsed = fs::read_to_string(path)
    .ok()
    .and_then(|text| serde_json::from_str::<Value>(&text).ok());
  if let Some(index) = parsed {
    if index.get("characters").and_then(Value::as_array).is_some() {
      return index;
    }
  }

  json!({
    "team": "fabled",
    "folder": "fabled",
    "characterCount": 0,
    "totalOccurrenceCount": 0,
    "characters": []
  })
}

fn read_character_index(directory: &Path, team: &str) -> Value {
  let path = directory.join("index.json");
  let parsed = fs::read_to_string(path)
    .ok()
    .and_then(|text| serde_json::from_str::<Value>(&text).ok());
  if let Some(index) = parsed {
    if index.get("characters").and_then(Value::as_array).is_some() {
      return index;
    }
  }

  json!({
    "team": team,
    "folder": character_folder(team).unwrap_or_else(|_| team.to_string()),
    "characterCount": 0,
    "totalOccurrenceCount": 0,
    "characters": []
  })
}

fn safe_custom_fabled_file_name(value: &str) -> String {
  let without_extension = value.strip_suffix(".json").unwrap_or(value);
  let sanitized = without_extension
    .trim()
    .chars()
    .map(|character| match character {
      '\\' | '/' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
      other => other,
    })
    .collect::<String>();
  format!("{}.json", if sanitized.is_empty() { "未命名传奇角色" } else { &sanitized })
}

fn safe_custom_character_file_name(value: &str) -> String {
  let without_extension = value.strip_suffix(".json").unwrap_or(value);
  let sanitized = without_extension
    .trim()
    .chars()
    .map(|character| match character {
      '\\' | '/' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
      other => other,
    })
    .collect::<String>();
  format!("{}.json", if sanitized.is_empty() { "未命名角色" } else { &sanitized })
}

fn normalize_character_team(team: &str) -> Result<String, String> {
  match team {
    "townsfolk" | "outsider" | "minion" | "demon" | "traveler" => Ok(team.to_string()),
    _ => Err(format!("Unsupported character team: {team}")),
  }
}

fn character_folder(team: &str) -> Result<String, String> {
  match team {
    "townsfolk" => Ok("townsfolks".to_string()),
    "outsider" => Ok("outsiders".to_string()),
    "minion" => Ok("minions".to_string()),
    "demon" => Ok("demons".to_string()),
    "traveler" => Ok("travelers".to_string()),
    _ => Err(format!("Unsupported character team: {team}")),
  }
}

fn json_text(value: Option<&Value>) -> String {
  value
    .and_then(Value::as_str)
    .unwrap_or_default()
    .trim()
    .to_string()
}

fn non_empty_text(value: String, fallback: &str) -> String {
  if value.is_empty() {
    fallback.to_string()
  } else {
    value
  }
}

fn main() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![
      fetch_image_data_url,
      save_custom_fabled_character,
      delete_fabled_character,
      save_custom_character,
      delete_character,
    ])
    .run(tauri::generate_context!())
    .expect("error while running Tauri application");
}
