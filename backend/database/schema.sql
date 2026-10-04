CREATE TABLE IF NOT EXISTS components (
  id INTEGER PRIMARY KEY,
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  quantity INTEGER NOT NULL CHECK(quantity >= 0),
  unit_price REAL NOT NULL CHECK(unit_price >= 0),
  supplier TEXT NOT NULL,
  reorder_level INTEGER NOT NULL DEFAULT 0 CHECK(reorder_level >= 0),
  image_path TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
