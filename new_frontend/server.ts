import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import duckdb from "duckdb";

const app = express();
const PORT = 3000;

// Universal BigInt serialization handler to prevent "Do not know how to serialize a BigInt" crashes in Express JSON responses
app.set("json replacer", (key: string, value: any) => {
  if (typeof value === "bigint") {
    return Number(value);
  }
  return value;
});

app.use(express.json());

// Cache for DuckDB connections to prevent open-handle warnings
const dbCache: { [key: string]: duckdb.Database } = {};

function getDbConnection(dbFile: string): duckdb.Database {
  const sanitizedName = dbFile.replace(/[^a-zA-Z0-9_\.-]/g, ""); // Security sanitization
  const dbPath = path.resolve(process.cwd(), sanitizedName);
  if (!dbCache[sanitizedName]) {
    dbCache[sanitizedName] = new duckdb.Database(dbPath);
  }
  return dbCache[sanitizedName];
}

// 1. Get available replay files and metadata
app.get("/api/replay/files", (req, res) => {
  const files = [
    { id: "20260407.duckdb", name: "Expiry 07-Apr-2026", date: "April 2026", description: "Standard Expiry Run (Weekly)" },
    { id: "20260413.duckdb", name: "Expiry 13-Apr-2026", date: "April 2026", description: "Standard Expiry Run (Weekly)" },
    { id: "20260421.duckdb", name: "Expiry 21-Apr-2026", date: "April 2026", description: "Standard Expiry Run (Weekly)" },
  ];
  res.json({ files });
});

// 1.5 Get available trading dates inside a database file
app.get("/api/replay/dates", (req, res) => {
  const { dbFile } = req.query;
  if (!dbFile || typeof dbFile !== "string") {
    return res.status(400).json({ error: "dbFile parameter is required" });
  }

  try {
    const db = getDbConnection(dbFile);
    db.all(
      `SELECT DISTINCT Date FROM spot_data ORDER BY Date ASC`,
      (err, rows) => {
        if (err) {
          console.error("Error retrieving dates:", err);
          return res.status(500).json({ error: err.message });
        }
        res.json({
          dbFile,
          dates: rows ? rows.map((r: any) => r.Date) : [],
        });
      }
    );
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 2. Fetch all chronological timestamps for a database, optionally filtered by date
app.get("/api/replay/timestamps", (req, res) => {
  const { dbFile, date } = req.query;
  if (!dbFile || typeof dbFile !== "string") {
    return res.status(400).json({ error: "dbFile parameter is required" });
  }

  try {
    const db = getDbConnection(dbFile);

    const callback = (err: any, rows: any) => {
      if (err) {
        console.error("Error retrieving timestamps:", err);
        return res.status(500).json({ error: err.message });
      }
      try {
        res.json({
          dbFile,
          selectedDate: date || "all",
          timestamps: rows ? rows.map((r: any) => ({
            timestamp: r.Timestamp,
            spotPrice: r.SpotPrice,
          })) : [],
        });
      } catch (serializeErr: any) {
        console.error("Serialization error in timestamps callback:", serializeErr);
        res.status(500).json({ error: serializeErr.message });
      }
    };

    if (date && typeof date === "string" && date !== "all") {
      const query = `SELECT Timestamp, Close as SpotPrice FROM spot_data WHERE Date = ? ORDER BY strptime(Timestamp, '%d-%m-%Y %H:%M:%S') ASC`;
      db.all(query, date, callback);
    } else {
      const query = `SELECT Timestamp, Close as SpotPrice FROM spot_data ORDER BY strptime(Timestamp, '%d-%m-%Y %H:%M:%S') ASC`;
      db.all(query, callback);
    }
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 3. Retrieve option metrics and spot candles at a specific historical timestamp for replay
app.get("/api/replay/record", (req, res) => {
  const { dbFile, timestamp } = req.query;
  if (!dbFile || typeof dbFile !== "string" || !timestamp || typeof timestamp !== "string") {
    return res.status(400).json({ error: "dbFile and timestamp parameters are required" });
  }

  try {
    const db = getDbConnection(dbFile);

    // Get current spot price row
    db.all(
      "SELECT * FROM spot_data WHERE Timestamp = ? LIMIT 1",
      timestamp,
      (err, spotRows) => {
        if (err) {
          console.error("Error querying spot_data:", err);
          return res.status(500).json({ error: err.message });
        }

        try {
          const rawSpot = spotRows && spotRows.length > 0 ? spotRows[0] : null;
          const spot = rawSpot ? {
            ...rawSpot,
            Volume: rawSpot.Volume !== null && rawSpot.Volume !== undefined ? Number(rawSpot.Volume) : 0,
            OI: rawSpot.OI !== null && rawSpot.OI !== undefined ? Number(rawSpot.OI) : 0,
          } : null;

          // Get options statistics underlay for that timestamp
          db.all(
            "SELECT Strike, OptionType, Open, High, Low, Close, Volume, OI, Ticker FROM options_data WHERE Timestamp = ?",
            timestamp,
            (errOpt, optionsRows) => {
              if (errOpt) {
                console.error("Error querying options_data:", errOpt);
                return res.status(500).json({ error: errOpt.message });
              }

              try {
                res.json({
                  timestamp,
                  spot,
                  options: optionsRows ? optionsRows.map((o: any) => ({
                    strike: Number(o.Strike),
                    optionType: o.OptionType,
                    open: Number(o.Open),
                    high: Number(o.High),
                    low: Number(o.Low),
                    close: Number(o.Close),
                    volume: o.Volume !== null && o.Volume !== undefined ? Number(o.Volume) : 0,
                    oi: o.OI !== null && o.OI !== undefined ? Number(o.OI) : 0,
                    ticker: o.Ticker,
                  })) : [],
                });
              } catch (jsonErr: any) {
                console.error("Error serializing response options:", jsonErr);
                res.status(500).json({ error: "Serialization error: " + jsonErr.message });
              }
            }
          );
        } catch (innerErr: any) {
          console.error("Error processing spot_data callback:", innerErr);
          res.status(500).json({ error: "Handler logic error: " + innerErr.message });
        }
      }
    );
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 3.5 Retrieve all option metrics and spot candles chronologically for fast overall backtesting
app.get("/api/replay/all-records", (req, res) => {
  const { dbFile, date } = req.query;
  if (!dbFile || typeof dbFile !== "string") {
    return res.status(400).json({ error: "dbFile parameter is required" });
  }

  try {
    const db = getDbConnection(dbFile);
    let spotQuery = `SELECT * FROM spot_data ORDER BY strptime(Timestamp, '%d-%m-%Y %H:%M:%S') ASC`;
    let optionsQuery = `SELECT Strike, OptionType, Open, High, Low, Close, Volume, OI, Ticker, Timestamp FROM options_data ORDER BY strptime(Timestamp, '%d-%m-%Y %H:%M:%S') ASC`;

    if (date && typeof date === "string" && date !== "all") {
      spotQuery = `SELECT * FROM spot_data WHERE Date = ? ORDER BY strptime(Timestamp, '%d-%m-%Y %H:%M:%S') ASC`;
      optionsQuery = `SELECT Strike, OptionType, Open, High, Low, Close, Volume, OI, Ticker, Timestamp FROM options_data WHERE Date = ? ORDER BY strptime(Timestamp, '%d-%m-%Y %H:%M:%S') ASC`;

      db.all(spotQuery, date, (err, spotRows) => {
        if (err) {
          console.error("Error querying all spot_data:", err);
          return res.status(500).json({ error: err.message });
        }
        db.all(optionsQuery, date, (errOpt, optionsRows) => {
          if (errOpt) {
            console.error("Error querying all options_data:", errOpt);
            return res.status(500).json({ error: errOpt.message });
          }
          res.json({
            spotRows: spotRows || [],
            optionsRows: optionsRows || [],
          });
        });
      });
    } else {
      db.all(spotQuery, (err, spotRows) => {
        if (err) {
          console.error("Error querying all spot_data:", err);
          return res.status(500).json({ error: err.message });
        }
        db.all(optionsQuery, (errOpt, optionsRows) => {
          if (errOpt) {
            console.error("Error querying all options_data:", errOpt);
            return res.status(500).json({ error: errOpt.message });
          }
          res.json({
            spotRows: spotRows || [],
            optionsRows: optionsRows || [],
          });
        });
      });
    }
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Health check API
app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

async function startServer() {
  // Vite dev server mounting in development mode
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Express server running on http://localhost:${PORT}`);
  });
}

startServer();
