/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Activity,
  Zap,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Play,
  Pause,
  Maximize2,
  Minimize2,
  RefreshCw,
  Plus,
  Minus,
  Layers,
  Database,
  Lock,
  Target,
  FileText,
  Sliders,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  X,
  User,
  ShoppingBag,
  Clock,
  Unlock,
  Cpu,
} from "lucide-react";
import {
  InstrumentType,
  ExpiryRegime,
  TradingBias,
  Candlestick,
  OptionStrikeData,
  OrderBook,
  Position,
  TradeSignal,
  WorkspaceConfig,
} from "./types";
import { MarketEngine } from "./utils/marketEngine";

export default function App() {
  // Config & Engine State
  const [config, setConfig] = useState<WorkspaceConfig>({
    layout: "side-by-side",
    isExpiryDay: false,
    oneClickEnabled: true,
    timeframeLock: "1m",
    speedMultiplier: 1,
    isHotKeysEnabled: true,
  });

  const [activeTab, setActiveTab] = useState<"terminal" | "pnl_analysis" | "strategy" | "integration">("terminal");

  // Simulation engine setup
  const [instrument, setInstrument] = useState<InstrumentType>(InstrumentType.NIFTY);
  const [engine, setEngine] = useState(() => new MarketEngine(InstrumentType.NIFTY, ExpiryRegime.STANDARD));
  const [isPlaying, setIsPlaying] = useState(true);

  // Trigger state updates
  const [spotPrice, setSpotPrice] = useState(engine.spotPrice);
  const [atmStrike, setAtmStrike] = useState(engine.atmStrike);
  const [strikes, setStrikes] = useState<OptionStrikeData[]>([]);
  const [spotCandles, setSpotCandles] = useState<Candlestick[]>([]);
  const [ceCandles, setCECandles] = useState<Candlestick[]>([]);
  const [peCandles, setPECandles] = useState<Candlestick[]>([]);
  const [ceOrderBook, setCEOrderBook] = useState<OrderBook>(engine.ceOrderBook);
  const [peOrderBook, setPEOrderBook] = useState<OrderBook>(engine.peOrderBook);
  const [signals, setSignals] = useState<TradeSignal[]>([]);
  const [coiPcr, setCoiPcr] = useState(1.0);
  const [windowStatus, setWindowStatus] = useState<string>("Aligned");
  const [gexProfile, setGexProfile] = useState<{ strike: number; gamma: number; callGEX: number; putGEX: number; netGEX: number }[]>([]);
  const [volatilityTrigger, setVolatilityTrigger] = useState<number>(0);

  // Positions State
  const [positions, setPositions] = useState<Position[]>([]);
  const [tradeHistory, setTradeHistory] = useState<Position[]>([]);
  const [isVolWeighted, setIsVolWeighted] = useState<boolean>(false);
  const [isTradeLogOpen, setIsTradeLogOpen] = useState<boolean>(false);
  const [accountBalance, setAccountBalance] = useState(500000); // 5 Lakhs Base INR
  const [tradeQuantity, setTradeQuantity] = useState(50); // Options lot multiplier (e.g. Nifty lot size)
  const [lastOrderAlert, setLastOrderAlert] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  // Interactive Chart state (Mouse scroll & zoom viewport)
  const [viewportCandles, setViewportCandles] = useState(35); // how many candles visible
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

  // Manual target / stop loss option
  const [useSLTP, setUseSLTP] = useState(true);
  const [slPercent, setSlPercent] = useState(10); // Default 10%
  const [tpPercent, setTpPercent] = useState(20); // Default 20%

  // External Integration Data States
  const [dataSource, setDataSource] = useState<"simulation" | "external" | "replay">("simulation");
  const [replayFiles, setReplayFiles] = useState<{ id: string; name: string; date: string; description: string }[]>([]);
  const [selectedReplayFile, setSelectedReplayFile] = useState<string>("20260421.duckdb");
  const [replayDates, setReplayDates] = useState<string[]>([]);
  const [selectedReplayDate, setSelectedReplayDate] = useState<string>("all");
  const [replayTimestamps, setReplayTimestamps] = useState<{ timestamp: string; spotPrice: number }[]>([]);
  const [replayCurrentIndex, setReplayCurrentIndex] = useState<number>(0);
  const [baseOI, setBaseOI] = useState<{ [key: string]: number }>({});
  const [isCompactHeader, setIsCompactHeader] = useState<boolean>(false);
  const [isAutoTrader, setIsAutoTrader] = useState<boolean>(false);
  const [replayLoading, setReplayLoading] = useState<boolean>(false);

  // Backtest & Dual-Replay state variables
  const [replayMode, setReplayMode] = useState<"visual" | "backtest">("visual");
  const [isBacktesting, setIsBacktesting] = useState<boolean>(false);
  const [backtestProgress, setBacktestProgress] = useState<{ current: number; total: number } | null>(null);
  const [backtestResult, setBacktestResult] = useState<{ completed: boolean; totalTrades: number; winRate: number; profit: number; compliance: number } | null>(null);

  const [pythonUrl, setPythonUrl] = useState("http://localhost:8000/api/quotes");
  const [isPolling, setIsPolling] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(2); // in seconds
  const [apiStatus, setApiStatus] = useState<"idle" | "fetching" | "connected" | "error">("idle");
  const [apiError, setApiError] = useState<string | null>(null);
  const [lastFeedTimestamp, setLastFeedTimestamp] = useState<string>("");
  const [manualPayloadText, setManualPayloadText] = useState(() => JSON.stringify({
    spotPrice: 22485.50,
    instrument: "NIFTY",
    strikeChain: [
      { strike: 22300, callOI: 12000, callCOI: 1200, callPremium: 210.5, putOI: 45000, putCOI: -500, putPremium: 12.5, callVolume: 15000, putVolume: 5000 },
      { strike: 22350, callOI: 18000, callCOI: 2300, callPremium: 165.2, putOI: 39000, putCOI: 4200, putPremium: 18.1, callVolume: 21000, putVolume: 8500 },
      { strike: 22400, callOI: 28000, callCOI: 4500, callPremium: 125.8, putOI: 31000, putCOI: 6800, putPremium: 28.5, callVolume: 35000, putVolume: 14000 },
      { strike: 22450, callOI: 45000, callCOI: 11000, callPremium: 92.4, putOI: 24000, putCOI: 9500, putPremium: 45.0, callVolume: 65000, putVolume: 25000 },
      { strike: 22500, callOI: 68000, callCOI: 18500, callPremium: 64.1, putOI: 15000, putCOI: 4200, putPremium: 66.8, callVolume: 98000, putVolume: 31050 },
      { strike: 22550, callOI: 52000, callCOI: 14000, callPremium: 42.5, putOI: 8000, putCOI: 1200, putPremium: 95.2, callVolume: 71000, putVolume: 12000 },
      { strike: 22600, callOI: 41000, callCOI: 8900, callPremium: 27.0, putOI: 4000, putCOI: 100, putPremium: 129.5, callVolume: 45000, putVolume: 4500 }
    ]
  }, null, 2));

  // --- TRADING TIMING CHECKS & STATS MATH ---
  const getTradingTimeStatus = (mode: "simulation" | "external" | "replay", replayCurrentTimeStr?: string) => {
    let hour = 9;
    let minute = 15;
    let second = 0;
    let timeStr = "09:15:00";

    if (mode === "replay" && replayCurrentTimeStr) {
      const parts = replayCurrentTimeStr.trim().split(/\s+/);
      const tPart = parts.length > 1 ? parts[1] : parts[0]; // e.g. "09:15:00"
      const tSub = tPart.split(":");
      if (tSub.length >= 2) {
        hour = parseInt(tSub[0], 10);
        minute = parseInt(tSub[1], 10);
        second = tSub.length > 2 ? parseInt(tSub[2], 10) : 0;
        timeStr = tPart;
      }
    } else {
      // simulation uses system clock
      const d = new Date();
      hour = d.getHours();
      minute = d.getMinutes();
      second = d.getSeconds();
      timeStr = d.toTimeString().split(" ")[0]; // "HH:MM:SS"
    }

    const totalMin = hour * 60 + minute;
    const isBefore0919 = totalMin < (9 * 60 + 19);
    const isAfter1515 = totalMin > (15 * 60 + 15);
    const isPast1525 = totalMin >= (15 * 60 + 25);

    return {
      hour,
      minute,
      second,
      timeStr,
      isBefore0919,
      isAfter1515,
      isPast1525,
    };
  };

  const pnlStats = useMemo(() => {
    const closedTrades = tradeHistory.filter((t) => t.status === "CLOSED");
    const activeTrades = tradeHistory.filter((t) => t.status === "ACTIVE");

    const totalTrades = tradeHistory.length;
    const closedCount = closedTrades.length;

    let totalRealizedPnL = closedTrades.reduce((acc, curr) => acc + curr.pnl, 0);
    let totalWinAmount = 0;
    let totalLossAmount = 0;
    let winCount = 0;
    let lossCount = 0;

    let ceCount = 0;
    let peCount = 0;
    let ceRealizedPnL = 0;
    let peRealizedPnL = 0;

    let largestWin = 0;
    let largestLoss = 0;

    // Rules Compliance metrics
    let rule1Violations = 0; // Trades before 09:19
    let rule2Violations = 0; // New entries after 15:15
    let rule3Violations = 0; // Forced close / left open after 15:25

    // Build cumulative timeline map
    let currentCurveSum = 0;
    const pnlCurvePoints = [{ index: 0, pnl: 0, balance: 500000 }];

    tradeHistory.forEach((t) => {
      let isViolatingR1 = false;
      let isViolatingR2 = false;

      if (t.timestamp) {
        const parts = t.timestamp.trim().split(/\s+/);
        const timePart = parts.length > 1 ? parts[1] : parts[0];
        const sub = timePart.split(":");
        if (sub.length >= 2) {
          const hr = parseInt(sub[0], 10);
          const min = parseInt(sub[1], 10);
          const totalMin = hr * 60 + min;
          if (totalMin < (9 * 60 + 19)) {
            rule1Violations++;
            isViolatingR1 = true;
          }
          if (totalMin > (15 * 60 + 15)) {
            rule2Violations++;
            isViolatingR2 = true;
          }
        }
      }

      if (t.status === "CLOSED") {
        currentCurveSum += t.pnl;
        pnlCurvePoints.push({
          index: pnlCurvePoints.length,
          pnl: t.pnl,
          balance: 500000 + currentCurveSum
        });

        if (t.pnl > 0) {
          winCount++;
          totalWinAmount += t.pnl;
          if (t.pnl > largestWin) largestWin = t.pnl;
        } else if (t.pnl < 0) {
          lossCount++;
          totalLossAmount += Math.abs(t.pnl);
          if (Math.abs(t.pnl) > largestLoss) largestLoss = Math.abs(t.pnl);
        }

        if (t.type === "CE") {
          ceCount++;
          ceRealizedPnL += t.pnl;
        } else {
          peCount++;
          peRealizedPnL += t.pnl;
        }

        if (t.exitTimeSec) {
          const dExit = new Date(t.exitTimeSec * 1000);
          const exitMin = dExit.getHours() * 60 + dExit.getMinutes();
          if (exitMin >= (15 * 60 + 25) && t.exitReason?.includes("15:25")) {
            rule3Violations++;
          }
        }
      } else {
        if (t.type === "CE") ceCount++;
        else peCount++;
      }
    });

    const winRate = closedCount > 0 ? (winCount / closedCount) * 100 : 0;
    const avgProfit = winCount > 0 ? totalWinAmount / winCount : 0;
    const avgLoss = lossCount > 0 ? totalLossAmount / lossCount : 0;
    const profitFactor = totalLossAmount > 0 ? totalWinAmount / totalLossAmount : totalWinAmount > 0 ? Infinity : 1;

    return {
      totalTrades,
      closedCount,
      activeCount: activeTrades.length,
      totalRealizedPnL,
      winCount,
      lossCount,
      winRate,
      avgProfit,
      avgLoss,
      profitFactor,
      largestWin,
      largestLoss,
      ceCount,
      peCount,
      ceRealizedPnL,
      peRealizedPnL,
      rule1Violations,
      rule2Violations,
      rule3Violations,
      pnlCurvePoints,
    };
  }, [tradeHistory]);

  const handleExportCSV = () => {
    if (tradeHistory.length === 0) {
      setLastOrderAlert({
        type: "error",
        msg: "No session trade history logs to export!",
      });
      return;
    }

    const csvRows = [
      ["Trade ID", "Instrument", "Option Type", "Strike", "Side", "Quantity", "Entry Price", "Exit Price", "Realized P&L", "Status", "Entry Time", "Exit Time", "Exit Reason"]
    ];

    tradeHistory.forEach((t) => {
      const entryTime = t.timestamp || "";
      const exitTime = t.exitTimeSec ? new Date(t.exitTimeSec * 1000).toLocaleTimeString() : "";
      csvRows.push([
        t.id,
        t.instrument,
        t.type,
        t.strike.toString(),
        t.side || "BUY",
        t.quantity.toString(),
        t.entryPrice.toFixed(2),
        t.exitPrice ? t.exitPrice.toFixed(2) : t.currentPrice.toFixed(2),
        t.pnl.toFixed(2),
        t.status,
        entryTime,
        exitTime,
        t.exitReason || ""
      ]);
    });

    const csvContent = "data:text/csv;charset=utf-8,"
      + csvRows.map(e => e.map(val => `"${val.toString().replace(/"/g, '""')}"`).join(",")).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `scalp_session_trades_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setLastOrderAlert({
      type: "success",
      msg: `Exported ${tradeHistory.length} trades to CSV for post-trade scalping analysis.`,
    });
  };

  // --- FAST BACKTEST IN-MEMORY SIMULATION ENGINE ---
  const runReplayBacktest = async () => {
    if (!selectedReplayFile) return;
    setIsBacktesting(true);
    setBacktestResult(null);
    setBacktestProgress({ current: 0, total: 100 });

    try {
      const res = await fetch(`/api/replay/all-records?dbFile=${selectedReplayFile}&date=${selectedReplayDate}`);
      const data = await res.json();
      if (!data || !data.spotRows || data.spotRows.length === 0) {
        setLastOrderAlert({
          type: "error",
          msg: "No trading records found inside DuckDB file to run backtest!",
        });
        setIsBacktesting(false);
        return;
      }

      const spotRows = data.spotRows;
      const optionsRows = data.optionsRows;

      const optionsByTimestamp: { [ts: string]: any[] } = {};
      optionsRows.forEach((o: any) => {
        const ts = o.Timestamp;
        if (!optionsByTimestamp[ts]) {
          optionsByTimestamp[ts] = [];
        }
        optionsByTimestamp[ts].push(o);
      });

      let pSpotCandles: Candlestick[] = [];
      let pCECandles: Candlestick[] = [];
      let pPECandles: Candlestick[] = [];
      let pPositions: Position[] = [];
      let pTradeHistory: Position[] = [];
      let pSignals: TradeSignal[] = [];
      let pBalance = 500000;
      let pBaseOI: { [key: string]: number } = {};

      const totalTicks = spotRows.length;

      for (let i = 0; i < totalTicks; i++) {
        const spot = spotRows[i];
        const ts = spot.Timestamp;
        const matchingOpts = optionsByTimestamp[ts] || [];

        const spotClose = Number(spot.Close);
        const spotOpen = Number(spot.Open);
        const spotHigh = Number(spot.High);
        const spotLow = Number(spot.Low);
        const spotVol = Number(spot.Volume || 0);

        const step = 50;
        const calculatedAtm = Math.round(spotClose / step) * step;

        const currentStrikes = [
          calculatedAtm - 3 * step,
          calculatedAtm - 2 * step,
          calculatedAtm - step,
          calculatedAtm,
          calculatedAtm + step,
          calculatedAtm + 2 * step,
          calculatedAtm + 3 * step,
        ];

        const calculatedChain: OptionStrikeData[] = currentStrikes.map((str) => {
          const callOption = matchingOpts.find((o: any) => Number(o.Strike) === str && o.OptionType === "CE");
          const putOption = matchingOpts.find((o: any) => Number(o.Strike) === str && o.OptionType === "PE");

          const callBaseKey = `${str}-CE`;
          const putBaseKey = `${str}-PE`;

          if (callOption && pBaseOI[callBaseKey] === undefined) {
            pBaseOI[callBaseKey] = Number(callOption.OI);
          }
          if (putOption && pBaseOI[putBaseKey] === undefined) {
            pBaseOI[putBaseKey] = Number(putOption.OI);
          }

          const callBaseVal = pBaseOI[callBaseKey] !== undefined ? pBaseOI[callBaseKey] : (callOption ? Number(callOption.OI) : 0);
          const putBaseVal = pBaseOI[putBaseKey] !== undefined ? pBaseOI[putBaseKey] : (putOption ? Number(putOption.OI) : 0);

          const callCOI = callOption ? Number(callOption.OI) - callBaseVal : 0;
          const putCOI = putOption ? Number(putOption.OI) - putBaseVal : 0;

          return {
            strike: str,
            callOI: callOption ? Number(callOption.OI) : 0,
            callCOI: callCOI,
            callPremium: callOption ? Number(callOption.Close) : 0,
            putOI: putOption ? Number(putOption.OI) : 0,
            putCOI: putCOI,
            putPremium: putOption ? Number(putOption.Close) : 0,
            callVolume: callOption ? Number(callOption.Volume) : 0,
            putVolume: putOption ? Number(putOption.Volume) : 0,
          };
        });

        let sumPutCOI = 0;
        let sumCallCOI = 0;
        calculatedChain.forEach((ch) => {
          sumPutCOI += Math.max(0, ch.putCOI);
          sumCallCOI += Math.max(0, ch.callCOI);
        });
        const roundedPcr = sumCallCOI === 0 ? 1.0 : Math.round((sumPutCOI / sumCallCOI) * 100) / 100;

        const timeSec = Math.floor(new Date(ts).getTime() / 1000) || (Math.floor(Date.now() / 1000) + i * 60);

        const newSpotCandle = { time: timeSec, open: spotOpen, high: spotHigh, low: spotLow, close: spotClose, volume: spotVol };
        pSpotCandles.push(newSpotCandle);
        if (pSpotCandles.length > 200) pSpotCandles.shift();
        computeCandleStats(pSpotCandles);

        const atmCall = matchingOpts.find((o: any) => Number(o.Strike) === calculatedAtm && o.OptionType === "CE");
        const newCECandle = {
          time: timeSec,
          open: atmCall ? Number(atmCall.Open) : spotClose - calculatedAtm,
          high: atmCall ? Number(atmCall.High) : spotClose - calculatedAtm,
          low: atmCall ? Number(atmCall.Low) : spotClose - calculatedAtm,
          close: atmCall ? Number(atmCall.Close) : spotClose - calculatedAtm,
          volume: atmCall ? Number(atmCall.Volume) : 0,
        };
        pCECandles.push(newCECandle);
        if (pCECandles.length > 200) pCECandles.shift();
        computeCandleStats(pCECandles);

        const atmPut = matchingOpts.find((o: any) => Number(o.Strike) === calculatedAtm && o.OptionType === "PE");
        const newPECandle = {
          time: timeSec,
          open: atmPut ? Number(atmPut.Open) : calculatedAtm - spotClose,
          high: atmPut ? Number(atmPut.High) : calculatedAtm - spotClose,
          low: atmPut ? Number(atmPut.Low) : calculatedAtm - spotClose,
          close: atmPut ? Number(atmPut.Close) : calculatedAtm - spotClose,
          volume: atmPut ? Number(atmPut.Volume) : 0,
        };
        pPECandles.push(newPECandle);
        if (pPECandles.length > 200) pPECandles.shift();
        computeCandleStats(pPECandles);

        const cePrice = atmCall ? Number(atmCall.Close) : 100;
        const pePrice = atmPut ? Number(atmPut.Close) : 90;

        pPositions = pPositions.map((pos) => {
          if (pos.exitReason) return pos;

          const contractMatch = matchingOpts.find((o: any) => Number(o.Strike) === pos.strike && o.OptionType === pos.type);
          const currentPremium = contractMatch ? Number(contractMatch.Close) : pos.currentPrice;
          const roundedLtp = Math.round(currentPremium * 100) / 100;

          const isShort = pos.side === "SELL";
          const pnl = isShort
            ? Math.round((pos.entryPrice - roundedLtp) * pos.quantity * 100) / 100
            : Math.round((roundedLtp - pos.entryPrice) * pos.quantity * 100) / 100;

          const isSlTriggered = isShort
            ? (pos.stopLoss ? roundedLtp >= pos.stopLoss : false)
            : (pos.stopLoss ? roundedLtp <= pos.stopLoss : false);

          const isTpTriggered = isShort
            ? (pos.takeProfit ? roundedLtp <= pos.takeProfit : false)
            : (pos.takeProfit ? roundedLtp >= pos.takeProfit : false);

          if (isSlTriggered || isTpTriggered) {
            const reason = isSlTriggered ? "SL Crossed" : "Target Met";
            const exitRef = {
              ...pos,
              status: "CLOSED" as const,
              exitSpot: spotClose,
              exitPrice: roundedLtp,
              pnl: pnl,
              exitReason: reason,
              exitTimeSec: timeSec,
            };

            const cashDelta = roundedLtp * pos.quantity;
            if (pos.side === "SELL") pBalance -= cashDelta;
            else pBalance += cashDelta;

            pTradeHistory.push(exitRef);
            return exitRef;
          }

          return { ...pos, currentPrice: roundedLtp, pnl };
        }).filter((p) => p.status === "ACTIVE");

        const hour = Number(ts.split(" ")[1]?.split(":")[0] || 9);
        const minute = Number(ts.split(" ")[1]?.split(":")[1] || 15);
        const totalMinutes = hour * 60 + minute;
        const isPast1525 = totalMinutes >= (15 * 60 + 25);
        const isBefore0919 = totalMinutes < (9 * 60 + 19);
        const isAfter1515 = totalMinutes > (15 * 60 + 15);

        if (isPast1525 && pPositions.length > 0) {
          pPositions.forEach((pos) => {
            const contractMatch = matchingOpts.find((o: any) => Number(o.Strike) === pos.strike && o.OptionType === pos.type);
            const currentPremium = contractMatch ? Number(contractMatch.Close) : pos.currentPrice;
            const roundedLtp = Math.round(currentPremium * 100) / 100;

            const pnl = pos.side === "SELL"
              ? Math.round((pos.entryPrice - roundedLtp) * pos.quantity * 100) / 100
              : Math.round((roundedLtp - pos.entryPrice) * pos.quantity * 100) / 100;

            const exitRef = {
              ...pos,
              status: "CLOSED" as const,
              exitSpot: spotClose,
              exitPrice: roundedLtp,
              pnl,
              exitReason: "Hard Square Off @ 15:25 (Rule 3)",
              exitTimeSec: timeSec,
            };

            const cashDelta = roundedLtp * pos.quantity;
            if (pos.side === "SELL") pBalance -= cashDelta;
            else pBalance += cashDelta;

            pTradeHistory.push(exitRef);
          });
          pPositions = [];
        }

        let trend: "Rising" | "Falling" | "Flat" = "Flat";
        if (pSpotCandles.length > 5) {
          const lastClose = spotClose;
          const prevClose = pSpotCandles[Math.max(0, pSpotCandles.length - 10)].close;
          const diff = lastClose - prevClose;
          trend = diff > 8 ? "Rising" : diff < -8 ? "Falling" : "Flat";
        }

        let maxCallOIStrike = calculatedAtm + 50;
        let maxCallOIVal = 0;
        let maxPutOIStrike = calculatedAtm - 50;
        let maxPutOIVal = 0;

        calculatedChain.forEach((ch) => {
          if (ch.callOI > maxCallOIVal) {
            maxCallOIVal = ch.callOI;
            maxCallOIStrike = ch.strike;
          }
          if (ch.putOI > maxPutOIVal) {
            maxPutOIVal = ch.putOI;
            maxPutOIStrike = ch.strike;
          }
        });

        let marketStructure: "Higher Highs / Lower Lows" | "Lower Highs / Lower Lows" | "Ranging" = "Ranging";
        if (pSpotCandles.length > 10) {
          const recent = pSpotCandles.slice(-10);
          const highest = Math.max(...recent.map((c) => c.high));
          const lowest = Math.min(...recent.map((c) => c.low));
          if (spotClose > highest - 10) {
            marketStructure = "Higher Highs / Lower Lows";
          } else if (spotClose < lowest + 10) {
            marketStructure = "Lower Highs / Lower Lows";
          }
        }

        let premiumSwings: "CE Breakout" | "PE Breakout" | "Compression" = "Compression";
        if (cePrice > 120 && roundedPcr > 1.1) {
          premiumSwings = "CE Breakout";
        } else if (pePrice > 110 && roundedPcr < 0.8) {
          premiumSwings = "PE Breakout";
        }

        let arrivalCoiShift: "Call Writing Spike at Resistance" | "Put Writing at Support" | "None" = "None";
        if (Math.abs(spotClose - maxCallOIStrike) < 15) {
          arrivalCoiShift = "Call Writing Spike at Resistance";
        } else if (Math.abs(spotClose - maxPutOIStrike) < 15) {
          arrivalCoiShift = "Put Writing at Support";
        }

        let institutionalContext: "Put Unwinding" | "Call Unwinding" | "Short Build-up" | "Long Liquidation" = "Short Build-up";
        if (roundedPcr > 1.3 && trend === "Rising") {
          institutionalContext = "Put Unwinding";
        } else if (roundedPcr < 0.7 && trend === "Falling") {
          institutionalContext = "Call Unwinding";
        } else if (roundedPcr >= 0.8 && roundedPcr <= 1.2) {
          institutionalContext = "Short Build-up";
        } else {
          institutionalContext = "Long Liquidation";
        }

        let bias = TradingBias.NEUTRAL;
        let action = "No Actions - PCR indices remain within standard neutral zones. Watch volume levels.";

        const bullTrigger = 1.2;
        const bearTrigger = 0.8;

        if (roundedPcr > bullTrigger) {
          const isStructureAlign = marketStructure === "Higher Highs / Lower Lows" || trend === "Rising";
          const isPremiumSwingAlign = premiumSwings === "CE Breakout" || cePrice > (pePrice * 1.2);
          if (isStructureAlign && isPremiumSwingAlign) {
            bias = TradingBias.HIGH_CONVICTION_BULLISH;
            action = `ENTER LONG OPTION SCALP (Buy ${calculatedAtm} CE). Target spot resistance wall at ${maxCallOIStrike}.`;
          } else {
            bias = TradingBias.NEUTRAL;
            action = `PCR suggests Bullish pressure (${roundedPcr.toFixed(2)}), waiting for Layer A structure or Layer B premium breakout.`;
          }
        } else if (roundedPcr < bearTrigger) {
          const isStructureAlign = marketStructure === "Lower Highs / Lower Lows" || trend === "Falling";
          const isPremiumSwingAlign = premiumSwings === "PE Breakout" || pePrice > (cePrice * 1.2);
          if (isStructureAlign && isPremiumSwingAlign) {
            bias = TradingBias.HIGH_CONVICTION_BEARISH;
            action = `ENTER SHORT OPTION SCALP (Buy ${calculatedAtm} PE). Target spot support wall at ${maxPutOIStrike}.`;
          } else {
            bias = TradingBias.NEUTRAL;
            action = `PCR suggests Bearish pressure (${roundedPcr.toFixed(2)}), waiting for confluence.`;
          }
        }

        if (trend === "Rising" && roundedPcr < bearTrigger) {
          bias = TradingBias.HARD_EXIT;
          action = "RETAIL BULL TRAP DETECTED. Price rising while PCR falling. Exit Call longs!";
        } else if (trend === "Falling" && roundedPcr > bullTrigger) {
          bias = TradingBias.HARD_EXIT;
          action = "SHORT TRAP DETECTED! Option writers selling Calls. Exit Put longs!";
        }

        const latestSignal: TradeSignal = {
          timestamp: ts,
          dayRegime: ExpiryRegime.STANDARD,
          indexTracked: InstrumentType.NIFTY,
          indexSpot: spotClose,
          atmStrike: calculatedAtm,
          windowStatus: "Aligned",
          currentCoiPcr: roundedPcr,
          trendLast30Min: trend,
          absoluteOiWalls: {
            callWallStrike: maxCallOIStrike,
            callWallVolume: maxCallOIVal,
            putWallStrike: maxPutOIStrike,
            putWallVolume: maxPutOIVal,
          },
          confluenceAnalysis: {
            marketStructure,
            premiumSwings,
            arrivalCoiShift,
            institutionalContext,
          },
          tradingBias: bias,
          action,
          isRead: false,
        };

        pSignals.unshift(latestSignal);
        if (pSignals.length > 50) pSignals.pop();

        const activePositionsExist = pPositions.some((p) => !p.exitReason);
        if (!activePositionsExist && isAutoTrader) {
          const allowEntry = !isBefore0919 && !isAfter1515 && !isPast1525;
          if (allowEntry) {
            let entryType: "CE" | "PE" | null = null;
            let entryPremium = 100;

            if (bias === TradingBias.HIGH_CONVICTION_BULLISH) {
              entryType = "CE";
              entryPremium = cePrice;
            } else if (bias === TradingBias.HIGH_CONVICTION_BEARISH) {
              entryType = "PE";
              entryPremium = pePrice;
            }

            if (entryType) {
              const roundedPremium = Math.round(entryPremium * 100) / 100;
              const marginNeeded = roundedPremium * tradeQuantity;

              if (pBalance >= marginNeeded) {
                const computedSL = useSLTP
                  ? Math.round(roundedPremium * (1 - slPercent / 100) * 100) / 100
                  : undefined;
                const computedTP = useSLTP
                  ? Math.round(roundedPremium * (1 + tpPercent / 100) * 100) / 100
                  : undefined;

                const orderId = "AUTO-BT-" + Math.random().toString(36).substring(3, 8).toUpperCase();
                const newPosition: Position = {
                  id: orderId,
                  instrument: InstrumentType.NIFTY,
                  type: entryType,
                  strike: calculatedAtm,
                  entryPrice: roundedPremium,
                  quantity: tradeQuantity,
                  currentPrice: roundedPremium,
                  stopLoss: computedSL,
                  takeProfit: computedTP,
                  pnl: 0,
                  timestamp: ts.split(" ")[1] || ts,
                  side: "BUY",
                  entrySpot: spotClose,
                  entryTimeSec: timeSec,
                  status: "ACTIVE",
                };

                pPositions.push(newPosition);
                pTradeHistory.push(newPosition);
                pBalance -= marginNeeded;
              }
            }
          }
        } else if (activePositionsExist && isAutoTrader && bias === TradingBias.HARD_EXIT) {
          pPositions.forEach((pos) => {
            const contractMatch = matchingOpts.find((o: any) => Number(o.Strike) === pos.strike && o.OptionType === pos.type);
            const currentPremium = contractMatch ? Number(contractMatch.Close) : pos.currentPrice;
            const roundedLtp = Math.round(currentPremium * 100) / 100;

            const pnl = pos.side === "SELL"
              ? Math.round((pos.entryPrice - roundedLtp) * pos.quantity * 100) / 100
              : Math.round((roundedLtp - pos.entryPrice) * pos.quantity * 100) / 100;

            const exitRef = {
              ...pos,
              status: "CLOSED" as const,
              exitSpot: spotClose,
              exitPrice: roundedLtp,
              pnl,
              exitReason: "Auto-Algo Close on TRAp/HARD_EXIT signal",
              exitTimeSec: timeSec,
            };

            const cashDelta = roundedLtp * pos.quantity;
            if (pos.side === "SELL") pBalance -= cashDelta;
            else pBalance += cashDelta;

            pTradeHistory.push(exitRef);
          });
          pPositions = [];
        }

        if (i % 25 === 0) {
          setBacktestProgress({ current: i, total: totalTicks });
        }
      }

      setAccountBalance(pBalance);
      setPositions(pPositions);
      setTradeHistory(pTradeHistory);
      setSignals(pSignals);
      setSpotPrice(spotRows[totalTicks - 1]?.Close || spotRows[0]?.Close);
      setAtmStrike(Math.round((spotRows[totalTicks - 1]?.Close || spotRows[0]?.Close) / 50) * 50);

      setSpotCandles(pSpotCandles);
      setCECandles(pCECandles);
      setPECandles(pPECandles);

      setReplayCurrentIndex(totalTicks - 1);

      const closedCount = pTradeHistory.filter((t) => t.status === "CLOSED").length;
      const winsCount = pTradeHistory.filter((t) => t.status === "CLOSED" && t.pnl > 0).length;
      const totalP = pTradeHistory.filter((t) => t.status === "CLOSED").reduce((acc, curr) => acc + curr.pnl, 0);

      let ruleViolationsCount = 0;
      pTradeHistory.forEach((t) => {
        if (t.timestamp) {
          const sub = t.timestamp.trim().split(/\s+/);
          const timeP = sub.length > 1 ? sub[1] : sub[0];
          const parts = timeP.split(":");
          if (parts.length >= 2) {
            const min = Number(parts[0]) * 60 + Number(parts[1]);
            if (min < (9 * 60 + 19) || min > (15 * 60 + 15)) {
              ruleViolationsCount++;
            }
          }
        }
      });

      const auditCompliance = Math.max(0, 100 - ruleViolationsCount * 10);

      setBacktestResult({
        completed: true,
        totalTrades: pTradeHistory.length,
        winRate: closedCount > 0 ? (winsCount / closedCount) * 100 : 0,
        profit: totalP,
        compliance: auditCompliance,
      });

      setLastOrderAlert({
        type: "success",
        msg: `Backtest completed! Found ${pTradeHistory.length} trading positions. Realized Net Profits: ₹${totalP.toLocaleString()}`,
      });

      setActiveTab("pnl_analysis");

    } catch (err: any) {
      console.error("Backtest failure:", err);
      setLastOrderAlert({
        type: "error",
        msg: `Backtest failed to execute: ${err.message}`,
      });
    } finally {
      setIsBacktesting(false);
      setBacktestProgress(null);
    }
  };

  // --- RULE 3 AUTOMATED HARD SQUARE OFF MONITOR ---
  useEffect(() => {
    const currentTimestampStr = dataSource === "replay"
      ? replayTimestamps[replayCurrentIndex]?.timestamp
      : undefined;

    const timeStatus = getTradingTimeStatus(dataSource, currentTimestampStr);

    if (timeStatus.isPast1525) {
      const activePositions = positions.filter((p) => !p.exitReason);
      if (activePositions.length > 0) {
        setLastOrderAlert({
          type: "error",
          msg: `[HARD SQUARE OFF ACTIVE] Time ${timeStatus.timeStr} is past 15:25 (Rule 3). Forcefully squaring off all scalps.`,
        });
        activePositions.forEach((pos) => {
          triggerMarketExit(pos.id, `Hard Square Off @ 15:25 (Rule 3)`);
        });
      }
    }
  }, [replayCurrentIndex, dataSource, positions, replayTimestamps]);

  // Update dynamic values from the marketEngine on ticks
  useEffect(() => {
    // If not in simulation mode, do not let local instantiator reset state
    if (dataSource !== "simulation") return;
    setSpotPrice(engine.spotPrice);
    setAtmStrike(engine.atmStrike);
    setStrikes([...engine.strikeChain]);
    setSpotCandles([...engine.spotCandles]);
    setCECandles([...engine.ceCandles]);
    setPECandles([...engine.peCandles]);
    setCEOrderBook({ ...engine.ceOrderBook });
    setPEOrderBook({ ...engine.peOrderBook });
    setSignals([...engine.signalsLog]);
    setCoiPcr(engine.getCOIPCR());
    setWindowStatus(engine.windowStatus);
    setGexProfile([...engine.getGEXProfile()]);
    setVolatilityTrigger(engine.getVolatilityTrigger());
  }, [engine, dataSource]);

  // Handle active instrument shifts
  const handleInstrumentChange = (newInst: InstrumentType) => {
    setInstrument(newInst);
    const newRegime = config.isExpiryDay ? ExpiryRegime.THURSDAY_EXPIRY : ExpiryRegime.STANDARD;
    const newEngine = new MarketEngine(newInst, newRegime);
    setEngine(newEngine);
    setTradeQuantity(newInst === InstrumentType.NIFTY ? 50 : 25); // Nifty 50 lot vs Banknifty 25
  };

  useEffect(() => {
    // Sync tradeQuantity automatically when instrument changes to guarantee multiples of lot size
    const lotSize = instrument === InstrumentType.NIFTY ? 50 : 25;
    setTradeQuantity((prev) => {
      if (prev % lotSize !== 0) {
        return lotSize;
      }
      return prev;
    });
  }, [instrument]);

  const toggleExpiryDay = () => {
    const nextExpiryState = !config.isExpiryDay;
    setConfig((prev) => ({ ...prev, isExpiryDay: nextExpiryState }));
    const newRegime = nextExpiryState ? ExpiryRegime.THURSDAY_EXPIRY : ExpiryRegime.STANDARD;
    const newEngine = new MarketEngine(instrument, newRegime);
    setEngine(newEngine);
  };

  // Live simulation tick cycle
  useEffect(() => {
    if (!isPlaying || dataSource !== "simulation") return;

    let subTickCount = 0;
    const timer = setInterval(() => {
      // Create tick walk
      const customBias = 0; // standard bias
      engine.triggerTick(customBias);

      subTickCount += 1;
      // Every 6 subTicks (e.g. 6 ticks = 1 simulated minute) we roll to a new candle
      if (subTickCount >= 6) {
        engine.rollMinute();
        subTickCount = 0;
      }

      // Update react view states
      setSpotPrice(engine.spotPrice);
      setAtmStrike(engine.atmStrike);
      setStrikes([...engine.strikeChain]);
      setSpotCandles([...engine.spotCandles]);
      setCECandles([...engine.ceCandles]);
      setPECandles([...engine.peCandles]);
      setCEOrderBook({ ...engine.ceOrderBook });
      setPEOrderBook({ ...engine.peOrderBook });
      setSignals([...engine.signalsLog]);
      setCoiPcr(engine.getCOIPCR());
      setWindowStatus(engine.windowStatus);
      setGexProfile([...engine.getGEXProfile()]);
      setVolatilityTrigger(engine.getVolatilityTrigger());

      // Re-evaluate dynamic trailing SL / TP limits on open positions
      setPositions((prev) =>
        prev.map((pos) => {
          const ltp = pos.type === "CE" ? engine.ceCandles[engine.ceCandles.length - 1].close : engine.peCandles[engine.peCandles.length - 1].close;
          const roundedLtp = Math.round(ltp * 100) / 100;

          const isShort = pos.side === "SELL";
          const pnl = isShort
            ? Math.round((pos.entryPrice - roundedLtp) * pos.quantity * 100) / 100
            : Math.round((roundedLtp - pos.entryPrice) * pos.quantity * 100) / 100;

          const isSlTriggered = isShort
            ? (pos.stopLoss ? roundedLtp >= pos.stopLoss : false)
            : (pos.stopLoss ? roundedLtp <= pos.stopLoss : false);

          const isTpTriggered = isShort
            ? (pos.takeProfit ? roundedLtp <= pos.takeProfit : false)
            : (pos.takeProfit ? roundedLtp >= pos.takeProfit : false);

          // Check automated SL / TP triggers
          if (isSlTriggered) {
            triggerMarketExit(pos.id, "SL Triggered Auto-Close");
            return { ...pos, currentPrice: roundedLtp, pnl, exitReason: "SL Crossed" };
          }
          if (isTpTriggered) {
            triggerMarketExit(pos.id, "TP Target Auto-Close");
            return { ...pos, currentPrice: roundedLtp, pnl, exitReason: "Target Met" };
          }

          return {
            ...pos,
            currentPrice: roundedLtp,
            pnl,
          };
        })
      );
    }, 1000 / config.speedMultiplier);

    return () => clearInterval(timer);
  }, [isPlaying, engine, config.speedMultiplier, dataSource]);

  // --- INSERTS START: REPLAY ENGINE & AUTO ALGO TRADING ARCHITECTURE ---
  // 1. Initial file loading on boot
  useEffect(() => {
    fetch("/api/replay/files")
      .then((res) => res.json())
      .then((data) => {
        if (data && data.files) {
          setReplayFiles(data.files);
        }
      })
      .catch((err) => console.error("Error loading replay files list:", err));
  }, []);

  // 1.5 Fetch available trading dates for selected db file
  useEffect(() => {
    if (!selectedReplayFile || dataSource !== "replay") return;
    fetch(`/api/replay/dates?dbFile=${selectedReplayFile}`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.dates && data.dates.length > 0) {
          setReplayDates(data.dates);
          // Auto-select the latest date (the last date in options collection)
          setSelectedReplayDate(data.dates[data.dates.length - 1]);
        } else {
          setReplayDates([]);
          setSelectedReplayDate("all");
        }
      })
      .catch((err) => {
        console.error("Error loading replay dates:", err);
        setReplayDates([]);
        setSelectedReplayDate("all");
      });
  }, [selectedReplayFile, dataSource]);

  // 2. Fetch timestamps of selected db file
  useEffect(() => {
    if (!selectedReplayFile || dataSource !== "replay") return;
    setReplayLoading(true);
    fetch(`/api/replay/timestamps?dbFile=${selectedReplayFile}&date=${selectedReplayDate}`)
      .then((res) => res.json())
      .then((data) => {
        setReplayLoading(false);
        if (data && data.timestamps) {
          setReplayTimestamps(data.timestamps);
          setReplayCurrentIndex(0);
          setBaseOI({}); // Clear cumulative Base OI

          // Clear previous candles to start a beautiful clean run
          setSpotCandles([]);
          setCECandles([]);
          setPECandles([]);
        }
      })
      .catch((err) => {
        setReplayLoading(false);
        console.error("Error loading replay timestamps:", err);
      });
  }, [selectedReplayFile, selectedReplayDate, dataSource]);

  // 3. Playback timer for Replay Mode
  useEffect(() => {
    if (dataSource !== "replay" || !isPlaying || replayTimestamps.length === 0) return;

    const timerInterval = setInterval(() => {
      setReplayCurrentIndex((prev) => {
        if (prev < replayTimestamps.length - 1) {
          return prev + 1;
        } else {
          setIsPlaying(false);
          setLastOrderAlert({
            type: "success",
            msg: "Historical DuckDB session replay completed successfully."
          });
          return prev;
        }
      });
    }, 1000 / config.speedMultiplier);

    return () => clearInterval(timerInterval);
  }, [dataSource, isPlaying, replayTimestamps, config.speedMultiplier]);

  // Helper functions for options GEX and zero-gamma math
  const calculateGammaValue = (S: number, K: number, T: number, sigma: number, r: number = 0.07): number => {
    if (S <= 0 || K <= 0 || T <= 0 || sigma <= 0) return 0;
    try {
      const d1 = (Math.log(S / K) + (r + (sigma * sigma) / 2) * T) / (sigma * Math.sqrt(T));
      const pdf = Math.exp(-0.5 * d1 * d1) / Math.sqrt(2 * Math.PI);
      return pdf / (S * sigma * Math.sqrt(T));
    } catch {
      return 0;
    }
  };

  const calculateGexProfile = (chain: OptionStrikeData[], spotVal: number) => {
    const T = 2.0 / 365;
    const sigma = 0.15;
    return chain.map((st) => {
      const gamma = calculateGammaValue(spotVal, st.strike, T, sigma);
      const callGEX = gamma * st.callOI * 100;
      const putGEX = gamma * st.putOI * 100;
      const netGEX = callGEX - putGEX;
      return {
        strike: st.strike,
        gamma,
        callGEX,
        putGEX,
        netGEX,
      };
    });
  };

  const calculateVolatilityTrigger = (chain: OptionStrikeData[], atmVal: number, spotVal: number) => {
    const step = 50;
    let bestSpot = spotVal;
    let minAbsNetGEX = Infinity;
    const T = 2.0 / 365;
    const sigma = 0.15;
    for (let testSpot = atmVal - 150; testSpot <= atmVal + 150; testSpot += 5) {
      let gexSum = 0;
      chain.forEach((st) => {
        const gamma = calculateGammaValue(testSpot, st.strike, T, sigma);
        gexSum += (gamma * st.callOI) - (gamma * st.putOI);
      });
      const absGexSum = Math.abs(gexSum);
      if (absGexSum < minAbsNetGEX) {
        minAbsNetGEX = absGexSum;
        bestSpot = testSpot;
      }
    }
    return Math.round(bestSpot * 100) / 100;
  };

  const computeCandleStats = (series: Candlestick[]) => {
    let cumVolume = 0;
    let cumPV = 0;
    for (let i = 0; i < series.length; i++) {
      const candle = series[i];
      const typicalPrice = (candle.high + candle.low + candle.close) / 3;
      cumVolume += candle.volume || 1;
      cumPV += typicalPrice * (candle.volume || 1);
      candle.vwap = Math.round((cumPV / cumVolume) * 100) / 100;

      if (i >= 8) {
        let sum = 0;
        if (i === 8) {
          for (let j = 0; j < 9; j++) sum += series[j].close;
          candle.ema = sum / 9;
        } else {
          const prevEma = series[i - 1].ema || series[i - 1].close;
          candle.ema = (candle.close * (2 / (9 + 1))) + (prevEma * (1 - (2 / (9 + 1))));
        }
      } else {
        candle.ema = candle.close;
      }
    }
  };

  const buildL2Depth = (ltp: number): OrderBook => {
    const bids: any[] = [];
    const asks: any[] = [];
    let maxQty = 0;
    for (let i = 1; i <= 10; i++) {
      const bidPrice = Math.round((ltp - i * 0.05) * 100) / 100;
      const askPrice = Math.round((ltp + i * 0.05) * 100) / 100;
      const bidQty = Math.floor((15 - i) * (200 + Math.random() * 400));
      const askQty = Math.floor((15 - i) * (180 + Math.random() * 420));
      bids.push({ price: bidPrice, quantity: bidQty, cumulativeDepth: 0, percentage: 0 });
      asks.push({ price: askPrice, quantity: askQty, cumulativeDepth: 0, percentage: 0 });
      maxQty = Math.max(maxQty, bidQty, askQty);
    }
    let bidCum = 0;
    bids.forEach((b) => {
      bidCum += b.quantity;
      b.cumulativeDepth = bidCum;
    });
    let askCum = 0;
    asks.forEach((a) => {
      askCum += a.quantity;
      a.cumulativeDepth = askCum;
    });
    bids.forEach((b) => (b.percentage = Math.round((b.quantity / maxQty) * 100)));
    asks.forEach((a) => (a.percentage = Math.round((a.quantity / maxQty) * 150)));
    return { bids, asks, maxQuantity: maxQty };
  };

  const executeOrderInReplay = (side: "BUY" | "SELL", type: "CE" | "PE", strike: number, premium: number) => {
    // Check Trading Timing Restrictions (Rules 1, 2, 3)
    const currentTimestampStr = replayTimestamps[replayCurrentIndex]?.timestamp;
    const timeStatus = getTradingTimeStatus("replay", currentTimestampStr);

    if (side === "BUY") {
      if (timeStatus.isBefore0919 || timeStatus.isAfter1515 || timeStatus.isPast1525) {
        console.log(`[AUTO-BOT SHIELD] Blocked automated buy order of ${type} at ${timeStatus.timeStr} due to timing boundary rules.`);
        return;
      }
    }

    const roundedPremium = Math.round(premium * 100) / 100;
    const marginNeeded = roundedPremium * tradeQuantity;

    if (side === "BUY" && accountBalance < marginNeeded) {
      return;
    }

    const computedSL = useSLTP
      ? (side === "BUY"
          ? Math.round(roundedPremium * (1 - slPercent / 100) * 100) / 100
          : Math.round(roundedPremium * (1 + slPercent / 100) * 100) / 100)
      : undefined;

    const computedTP = useSLTP
      ? (side === "BUY"
          ? Math.round(roundedPremium * (1 + tpPercent / 100) * 100) / 100
          : Math.round(roundedPremium * (1 - tpPercent / 100) * 100) / 100)
      : undefined;

    const orderId = "AUTO-" + Math.random().toString(36).substring(3, 8).toUpperCase();

    const newPosition: Position = {
      id: orderId,
      instrument: InstrumentType.NIFTY,
      type,
      strike,
      entryPrice: roundedPremium,
      quantity: tradeQuantity,
      currentPrice: roundedPremium,
      stopLoss: computedSL,
      takeProfit: computedTP,
      pnl: 0,
      timestamp: new Date().toLocaleTimeString(),
      side,
      entrySpot: spotPrice,
      entryTimeSec: spotCandles[spotCandles.length - 1]?.time || Math.floor(Date.now() / 1000),
      status: "ACTIVE",
    };

    setPositions((prev) => [...prev, newPosition]);
    setTradeHistory((prev) => [...prev, newPosition]);

    if (side === "BUY") {
      setAccountBalance((prev) => prev - marginNeeded);
    } else {
      setAccountBalance((prev) => prev + marginNeeded);
    }

    setLastOrderAlert({
      type: "success",
      msg: `[AUTO-ALGO TRADER EXECUTION] Bought NIFTY ${strike} ${type} at ₹${roundedPremium} x ${tradeQuantity}`,
    });
  };

  const evaluateReplayStrategyRules = (
    timestampStr: string,
    spotVal: number,
    atmVal: number,
    chain: OptionStrikeData[],
    pcrVal: number,
    openVal: number,
    highVal: number,
    lowVal: number,
    lastCEPremium: number,
    lastPEPremium: number
  ) => {
    let trend: "Rising" | "Falling" | "Flat" = "Flat";
    if (spotCandles.length > 5) {
      const lastClose = spotVal;
      const prevClose = spotCandles[Math.max(0, spotCandles.length - 10)].close;
      const diff = lastClose - prevClose;
      trend = diff > 8 ? "Rising" : diff < -8 ? "Falling" : "Flat";
    }

    let maxCallOIStrike = atmVal + 50;
    let maxCallOIVal = 0;
    let maxPutOIStrike = atmVal - 50;
    let maxPutOIVal = 0;

    chain.forEach((ch) => {
      if (ch.callOI > maxCallOIVal) {
        maxCallOIVal = ch.callOI;
        maxCallOIStrike = ch.strike;
      }
      if (ch.putOI > maxPutOIVal) {
        maxPutOIVal = ch.putOI;
        maxPutOIStrike = ch.strike;
      }
    });

    let marketStructure: "Higher Highs / Lower Lows" | "Lower Highs / Lower Lows" | "Ranging" = "Ranging";
    if (spotCandles.length > 10) {
      const recent = spotCandles.slice(-10);
      const highest = Math.max(...recent.map((c) => c.high));
      const lowest = Math.min(...recent.map((c) => c.low));
      if (spotVal > highest - 10) {
        marketStructure = "Higher Highs / Lower Lows";
      } else if (spotVal < lowest + 10) {
        marketStructure = "Lower Highs / Lower Lows";
      }
    }

    let premiumSwings: "CE Breakout" | "PE Breakout" | "Compression" = "Compression";
    if (lastCEPremium > 120 && pcrVal > 1.1) {
      premiumSwings = "CE Breakout";
    } else if (lastPEPremium > 110 && pcrVal < 0.8) {
      premiumSwings = "PE Breakout";
    }

    let arrivalCoiShift: "Call Writing Spike at Resistance" | "Put Writing at Support" | "None" = "None";
    if (Math.abs(spotVal - maxCallOIStrike) < 15) {
      arrivalCoiShift = "Call Writing Spike at Resistance";
    } else if (Math.abs(spotVal - maxPutOIStrike) < 15) {
      arrivalCoiShift = "Put Writing at Support";
    }

    let institutionalContext: "Put Unwinding" | "Call Unwinding" | "Short Build-up" | "Long Liquidation" = "Short Build-up";
    if (pcrVal > 1.3 && trend === "Rising") {
      institutionalContext = "Put Unwinding";
    } else if (pcrVal < 0.7 && trend === "Falling") {
      institutionalContext = "Call Unwinding";
    } else if (pcrVal >= 0.8 && pcrVal <= 1.2) {
      institutionalContext = "Short Build-up";
    } else {
      institutionalContext = "Long Liquidation";
    }

    let bias = TradingBias.NEUTRAL;
    let action = "No Actions - PCR indices remain within standard neutral zones. Watch volume levels.";

    const bullTrigger = 1.2;
    const bearTrigger = 0.8;

    if (pcrVal > bullTrigger) {
      const isStructureAlign = marketStructure === "Higher Highs / Lower Lows" || trend === "Rising";
      const isPremiumSwingAlign = premiumSwings === "CE Breakout" || lastCEPremium > (lastPEPremium * 1.2);
      if (isStructureAlign && isPremiumSwingAlign) {
        bias = TradingBias.HIGH_CONVICTION_BULLISH;
        action = `ENTER LONG OPTION SCALP (Buy ${atmVal} CE). Target spot resistance wall at ${maxCallOIStrike}.`;
      } else {
        bias = TradingBias.NEUTRAL;
        action = `PCR suggests Bullish pressure (${pcrVal.toFixed(2)}), waiting for Layer A structure or Layer B premium breakout.`;
      }
    } else if (pcrVal < bearTrigger) {
      const isStructureAlign = marketStructure === "Lower Highs / Lower Lows" || trend === "Falling";
      const isPremiumSwingAlign = premiumSwings === "PE Breakout" || lastPEPremium > (lastCEPremium * 1.2);
      if (isStructureAlign && isPremiumSwingAlign) {
        bias = TradingBias.HIGH_CONVICTION_BEARISH;
        action = `ENTER SHORT OPTION SCALP (Buy ${atmVal} PE). Target spot support wall at ${maxPutOIStrike}.`;
      } else {
        bias = TradingBias.NEUTRAL;
        action = `PCR suggests Bearish pressure (${pcrVal.toFixed(2)}), waiting for confluence.`;
      }
    }

    if (trend === "Rising" && pcrVal < bearTrigger) {
      bias = TradingBias.HARD_EXIT;
      action = "RETAIL BULL TRAP DETECTED. Price rising while PCR falling. Exit Call longs!";
    } else if (trend === "Falling" && pcrVal > bullTrigger) {
      bias = TradingBias.HARD_EXIT;
      action = "SHORT TRAP DETECTED! Option writers selling Calls. Exit Put longs!";
    }

    const latestSignal: TradeSignal = {
      timestamp: timestampStr,
      dayRegime: ExpiryRegime.STANDARD,
      indexTracked: InstrumentType.NIFTY,
      indexSpot: spotVal,
      atmStrike: atmVal,
      windowStatus: "Aligned",
      currentCoiPcr: pcrVal,
      trendLast30Min: trend,
      absoluteOiWalls: {
        callWallStrike: maxCallOIStrike,
        callWallVolume: maxCallOIVal,
        putWallStrike: maxPutOIStrike,
        putWallVolume: maxPutOIVal,
      },
      confluenceAnalysis: {
        marketStructure,
        premiumSwings,
        arrivalCoiShift,
        institutionalContext,
      },
      tradingBias: bias,
      action,
      isRead: false,
    };

    setSignals((prev) => [latestSignal, ...prev.slice(0, 49)]);

    // Trigger auto order if enabled
    if (isAutoTrader) {
      const activePositionsExist = positions.some((p) => !p.exitReason);
      if (!activePositionsExist) {
        if (bias === TradingBias.HIGH_CONVICTION_BULLISH) {
          executeOrderInReplay("BUY", "CE", atmVal, lastCEPremium);
        } else if (bias === TradingBias.HIGH_CONVICTION_BEARISH) {
          executeOrderInReplay("BUY", "PE", atmVal, lastPEPremium);
        }
      } else {
        if (bias === TradingBias.HARD_EXIT) {
          positions.forEach((pos) => {
            if (!pos.exitReason) {
              triggerMarketExit(pos.id, "Auto-Algo Close on TRAp/HARD_EXIT signal");
            }
          });
        }
      }
    }
  };

  // 4. Sequence driver for processing each Replay Index tick
  useEffect(() => {
    if (dataSource !== "replay" || replayTimestamps.length === 0 || replayCurrentIndex >= replayTimestamps.length) return;

    const currentItem = replayTimestamps[replayCurrentIndex];
    if (!currentItem) return;

    const fetchReplayTick = async () => {
      try {
        const res = await fetch(`/api/replay/record?dbFile=${selectedReplayFile}&timestamp=${encodeURIComponent(currentItem.timestamp)}`);
        const data = await res.json();
        if (!data || !data.spot) return;

        const currentSpot = Number(data.spot.Close);
        const spotOpen = Number(data.spot.Open);
        const spotHigh = Number(data.spot.High);
        const spotLow = Number(data.spot.Low);
        const spotClose = Number(data.spot.Close);
        const spotVol = Number(data.spot.Volume || 0);

        setSpotPrice(spotClose);

        const step = 50;
        const calculatedAtm = Math.round(spotClose / step) * step;
        setAtmStrike(calculatedAtm);

        // ATM +/- 3 strikes
        const currentStrikes = [
          calculatedAtm - 3 * step,
          calculatedAtm - 2 * step,
          calculatedAtm - step,
          calculatedAtm,
          calculatedAtm + step,
          calculatedAtm + 2 * step,
          calculatedAtm + 3 * step,
        ];

        // Map Option chain data
        const calculatedChain: OptionStrikeData[] = currentStrikes.map((str) => {
          const callOption = data.options.find((o: any) => o.strike === str && o.optionType === "CE");
          const putOption = data.options.find((o: any) => o.strike === str && o.optionType === "PE");

          const callBaseKey = `${str}-CE`;
          const putBaseKey = `${str}-PE`;

          let callCOI = 0;
          let putCOI = 0;

          setBaseOI((prev) => {
            const next = { ...prev };
            if (callOption && next[callBaseKey] === undefined) {
              next[callBaseKey] = callOption.oi;
            }
            if (putOption && next[putBaseKey] === undefined) {
              next[putBaseKey] = putOption.oi;
            }
            return next;
          });

          // Compute Change in OI relative to base dictionary
          const callBaseVal = baseOI[callBaseKey] !== undefined ? baseOI[callBaseKey] : (callOption ? callOption.oi : 0);
          const putBaseVal = baseOI[putBaseKey] !== undefined ? baseOI[putBaseKey] : (putOption ? putOption.oi : 0);

          if (callOption) callCOI = callOption.oi - callBaseVal;
          if (putOption) putCOI = putOption.oi - putBaseVal;

          return {
            strike: str,
            callOI: callOption ? callOption.oi : 0,
            callCOI: callCOI,
            callPremium: callOption ? callOption.close : 0,
            putOI: putOption ? putOption.oi : 0,
            putCOI: putCOI,
            putPremium: putOption ? putOption.close : 0,
            callVolume: callOption ? callOption.volume : 0,
            putVolume: putOption ? putOption.volume : 0,
          };
        });

        setStrikes(calculatedChain);

        // COI Put/Call Ratio
        let sumPutCOI = 0;
        let sumCallCOI = 0;
        calculatedChain.forEach((ch) => {
          sumPutCOI += Math.max(0, ch.putCOI);
          sumCallCOI += Math.max(0, ch.callCOI);
        });
        const finalPcr = sumCallCOI === 0 ? 1.0 : sumPutCOI / sumCallCOI;
        const roundedPcr = Math.round(finalPcr * 100) / 100;
        setCoiPcr(roundedPcr);

        // Convert db timestamp string to seconds
        const timeSec = Math.floor(new Date(currentItem.timestamp).getTime() / 1000) || (Math.floor(Date.now() / 1000) + replayCurrentIndex * 60);

        // Add Spot candle record
        const newSpotCandle = {
          time: timeSec,
          open: spotOpen,
          high: spotHigh,
          low: spotLow,
          close: spotClose,
          volume: spotVol,
        };

        const atmCall = data.options.find((o: any) => o.strike === calculatedAtm && o.optionType === "CE");
        const newCECandle = {
          time: timeSec,
          open: atmCall ? atmCall.open : spotClose - calculatedAtm,
          high: atmCall ? atmCall.high : spotClose - calculatedAtm,
          low: atmCall ? atmCall.low : spotClose - calculatedAtm,
          close: atmCall ? atmCall.close : spotClose - calculatedAtm,
          volume: atmCall ? atmCall.volume : 0,
        };

        const atmPut = data.options.find((o: any) => o.strike === calculatedAtm && o.optionType === "PE");
        const newPECandle = {
          time: timeSec,
          open: atmPut ? atmPut.open : calculatedAtm - spotClose,
          high: atmPut ? atmPut.high : calculatedAtm - spotClose,
          low: atmPut ? atmPut.low : calculatedAtm - spotClose,
          close: atmPut ? atmPut.close : calculatedAtm - spotClose,
          volume: atmPut ? atmPut.volume : 0,
        };

        setSpotCandles((prev) => {
          const list = [...prev, newSpotCandle];
          if (list.length > 200) list.shift();
          computeCandleStats(list);
          return list;
        });

        setCECandles((prev) => {
          const list = [...prev, newCECandle];
          if (list.length > 200) list.shift();
          computeCandleStats(list);
          return list;
        });

        setPECandles((prev) => {
          const list = [...prev, newPECandle];
          if (list.length > 200) list.shift();
          computeCandleStats(list);
          return list;
        });

        const cePrice = atmCall ? atmCall.close : 100;
        const pePrice = atmPut ? atmPut.close : 90;

        setCEOrderBook(buildL2Depth(cePrice));
        setPEOrderBook(buildL2Depth(pePrice));

        setGexProfile(calculateGexProfile(calculatedChain, spotClose));
        setVolatilityTrigger(calculateVolatilityTrigger(calculatedChain, calculatedAtm, spotClose));

        // Evaluate Strategy Rules
        evaluateReplayStrategyRules(
          currentItem.timestamp,
          spotClose,
          calculatedAtm,
          calculatedChain,
          roundedPcr,
          spotOpen,
          spotHigh,
          spotLow,
          cePrice,
          pePrice
        );

        // Update positions P&L and dynamic triggers
        setPositions((positionsList) =>
          positionsList.map((pos) => {
            if (pos.exitReason) return pos;

            // Check matching option price in current ticks data map
            const contractMatch = data.options.find((o: any) => o.strike === pos.strike && o.optionType === pos.type);
            const currentPremium = contractMatch ? contractMatch.close : pos.currentPrice;
            const roundedLtp = Math.round(currentPremium * 100) / 100;

            const isShort = pos.side === "SELL";
            const pnl = isShort
              ? Math.round((pos.entryPrice - roundedLtp) * pos.quantity * 100) / 100
              : Math.round((roundedLtp - pos.entryPrice) * pos.quantity * 100) / 100;

            const isSlTriggered = isShort
              ? (pos.stopLoss ? roundedLtp >= pos.stopLoss : false)
              : (pos.stopLoss ? roundedLtp <= pos.stopLoss : false);

            const isTpTriggered = isShort
              ? (pos.takeProfit ? roundedLtp <= pos.takeProfit : false)
              : (pos.takeProfit ? roundedLtp >= pos.takeProfit : false);

            if (isSlTriggered) {
              triggerMarketExit(pos.id, "Stop Loss Dynamic Replay Cut-out");
              return { ...pos, currentPrice: roundedLtp, pnl, exitReason: "SL Crossed" };
            }
            if (isTpTriggered) {
              triggerMarketExit(pos.id, "Take Profit Target Replay Met");
              return { ...pos, currentPrice: roundedLtp, pnl, exitReason: "Target Met" };
            }

            return {
              ...pos,
              currentPrice: roundedLtp,
              pnl,
            };
          })
        );

      } catch (err) {
        console.error("Error executing replay index state tick:", err);
      }
    };

    fetchReplayTick();
  }, [replayCurrentIndex, dataSource]);
  // --- INSERTS END: REPLAY ENGINE & AUTO ALGO TRADING ARCHITECTURE ---

  // Polling loop for active Python server ingestion
  useEffect(() => {
    if (dataSource !== "external" || !isPolling) {
      if (dataSource === "simulation") {
        setApiStatus("idle");
      }
      return;
    }

    const fetchFeed = async () => {
      setApiStatus("fetching");
      try {
        const response = await fetch(pythonUrl, {
          method: "GET",
          headers: {
            "Accept": "application/json",
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP Error: ${response.status} - ${response.statusText}`);
        }

        const data = await response.json();

        if (data && typeof data === "object") {
          const loadedSpot = Number(data.spotPrice || 22450);
          const loadedStrikes = Array.isArray(data.strikeChain) ? data.strikeChain : [];

          if (loadedStrikes.length === 0) {
            throw new Error("Invalid payload: strikeChain list is empty.");
          }

          // Verify strikes format has required keys
          const sanitizedStrikes = loadedStrikes.map((s: any) => ({
            strike: Number(s.strike || 0),
            callOI: Number(s.callOI || 0),
            callCOI: Number(s.callCOI || 0),
            callPremium: Number(s.callPremium || 0),
            putOI: Number(s.putOI || 0),
            putCOI: Number(s.putCOI || 0),
            putPremium: Number(s.putPremium || 0),
            callVolume: Number(s.callVolume || 0),
            putVolume: Number(s.putVolume || 0),
          }));

          // Update the options engine state
          engine.updateExternalData(loadedSpot, sanitizedStrikes);

          // Trigger the state updates inside the app to refresh drawings
          setSpotPrice(engine.spotPrice);
          setAtmStrike(engine.atmStrike);
          setStrikes([...engine.strikeChain]);
          setGexProfile([...engine.getGEXProfile()]);
          setVolatilityTrigger(engine.getVolatilityTrigger());
          setCoiPcr(engine.getCOIPCR());
          setWindowStatus(engine.windowStatus);

          setApiStatus("connected");
          setApiError(null);
          setLastFeedTimestamp(new Date().toLocaleTimeString());
        } else {
          throw new Error("Response content is not a valid JSON dictionary.");
        }
      } catch (err: any) {
        setApiStatus("error");
        setApiError(err.message || "Failed to make HTTP GET request to local Python webserver.");
      }
    };

    // Run first call immediately
    fetchFeed();

    const intervalTimer = setInterval(() => {
      fetchFeed();
    }, pollingInterval * 1000);

    return () => clearInterval(intervalTimer);
  }, [dataSource, isPolling, pythonUrl, pollingInterval, engine]);

  // Handle direct manual JSON payload injection
  const handleManualPayloadInject = () => {
    try {
      const parsed = JSON.parse(manualPayloadText);
      if (!parsed || typeof parsed !== "object") {
        throw new Error("Payload must be a valid JSON dictionary.");
      }

      const loadedSpot = Number(parsed.spotPrice);
      if (isNaN(loadedSpot) || loadedSpot <= 0) {
        throw new Error("Invalid or missing 'spotPrice': must be a positive number.");
      }

      if (!Array.isArray(parsed.strikeChain) || parsed.strikeChain.length === 0) {
        throw new Error("Invalid or missing 'strikeChain': must be a non-empty array.");
      }

      // Sanitize structures
      const sanitizedStrikes = parsed.strikeChain.map((s: any, idx: number) => {
        if (typeof s.strike !== "number") {
          throw new Error(`Strike item at index ${idx} is missing a numerical 'strike' key.`);
        }
        return {
          strike: Number(s.strike || 0),
          callOI: Number(s.callOI || 0),
          callCOI: Number(s.callCOI || 0),
          callPremium: Number(s.callPremium || 0),
          putOI: Number(s.putOI || 0),
          putCOI: Number(s.putCOI || 0),
          putPremium: Number(s.putPremium || 0),
          callVolume: Number(s.callVolume || 0),
          putVolume: Number(s.putVolume || 0),
        };
      });

      // Check if instrument matches
      if (parsed.instrument && parsed.instrument !== instrument) {
        setInstrument(parsed.instrument);
      }

      // Update engine
      engine.updateExternalData(loadedSpot, sanitizedStrikes);

      // Refresh React Views
      setSpotPrice(engine.spotPrice);
      setAtmStrike(engine.atmStrike);
      setStrikes([...engine.strikeChain]);
      setGexProfile([...engine.getGEXProfile()]);
      setVolatilityTrigger(engine.getVolatilityTrigger());
      setCoiPcr(engine.getCOIPCR());
      setWindowStatus(engine.windowStatus);

      // Notify user
      setLastOrderAlert({
        type: "success",
        msg: `Successfully injected payload! Spot and GEX curves recalculated. Data source swapped to External.`,
      });
      setDataSource("external");
      setApiStatus("connected");
      setApiError(null);
      setLastFeedTimestamp(new Date().toLocaleTimeString());
    } catch (err: any) {
      setLastOrderAlert({
        type: "error",
        msg: `Failed to inject JSON payload: ${err.message}`,
      });
    }
  };

  const loadTestingPreset = (type: "bullish" | "bearish") => {
    let preset;
    if (type === "bullish") {
      preset = {
        spotPrice: 22610.00,
        instrument: "NIFTY",
        strikeChain: [
          { strike: 22450, callOI: 15400, callCOI: 1100, callPremium: 202.5, putOI: 62000, putCOI: 9500, putPremium: 11.2, callVolume: 12000, putVolume: 18000 },
          { strike: 22500, callOI: 19800, callCOI: 1900, callPremium: 155.0, putOI: 54000, putCOI: 11200, putPremium: 16.5, callVolume: 19000, putVolume: 28000 },
          { strike: 22550, callOI: 28000, callCOI: 2400, callPremium: 112.5, putOI: 41000, putCOI: 12100, putPremium: 25.1, callVolume: 35000, putVolume: 49000 },
          { strike: 22600, callOI: 45000, callCOI: 3900, putOI: 38000, putCOI: 16400, putPremium: 43.0, callVolume: 61000, putVolume: 74000, callPremium: 78.4 },
          { strike: 22650, callOI: 82000, callCOI: 21500, callPremium: 51.2, putOI: 18000, putCOI: 3800, putPremium: 68.4, callVolume: 120500, putVolume: 25000 },
          { strike: 22700, callOI: 96000, callCOI: 28400, callPremium: 32.5, putOI: 6200, putCOI: 150, putPremium: 98.1, callVolume: 145000, putVolume: 8000 },
          { strike: 22750, callOI: 61000, callCOI: 13200, callPremium: 18.0, putOI: 2100, putCOI: 0, putPremium: 135.5, callVolume: 92000, putVolume: 2100 }
        ]
      };
    } else {
      preset = {
        spotPrice: 22320.00,
        instrument: "NIFTY",
        strikeChain: [
          { strike: 22150, callOI: 62000, callCOI: 14500, callPremium: 215.1, putOI: 7800, putCOI: 100, putPremium: 28.5, callVolume: 85000, putVolume: 5100 },
          { strike: 22200, callOI: 69000, callCOI: 17800, callPremium: 168.0, putOI: 9200, putCOI: 250, putPremium: 39.5, callVolume: 99000, putVolume: 7400 },
          { strike: 22250, callOI: 74000, callCOI: 20100, callPremium: 125.4, putOI: 11000, putCOI: 410, putPremium: 56.4, callVolume: 112000, putVolume: 8200 },
          { strike: 22300, callOI: 88000, callCOI: 28000, callPremium: 89.2, putOI: 15200, putCOI: -1200, putPremium: 81.0, callVolume: 165000, putVolume: 14000 },
          { strike: 22350, callOI: 72000, callCOI: 14205, callPremium: 58.0, putOI: 6500, putCOI: -800, putPremium: 118.2, callVolume: 124000, putVolume: 3900 },
          { strike: 22400, callOI: 58000, callCOI: 11200, callPremium: 34.5, putOI: 2800, putCOI: -200, putPremium: 154.0, callVolume: 84000, putVolume: 1100 },
          { strike: 22450, callOI: 39000, callCOI: 6500, callPremium: 19.1, putOI: 1100, putCOI: -50, putPremium: 205.1, callVolume: 49000, putVolume: 350 }
        ]
      };
    }
    setManualPayloadText(JSON.stringify(preset, null, 2));
    setLastOrderAlert({
      type: "success",
      msg: `Loaded preset payload. Click 'Inject JSON' to apply!`,
    });
  };

  // One-Click Order execution protocols
  const executeOrder = (side: "BUY" | "SELL", type: "CE" | "PE", customStrike?: number) => {
    // Check Trading Timing Restrictions (Rules 1, 2, 3)
    const currentTimestampStr = dataSource === "replay"
      ? replayTimestamps[replayCurrentIndex]?.timestamp
      : undefined;

    const timeStatus = getTradingTimeStatus(dataSource, currentTimestampStr);

    if (side === "BUY") {
      if (timeStatus.isBefore0919) {
        setLastOrderAlert({
          type: "error",
          msg: `[RULE VIOLATION] Trade blocked! Rule 1: No trades allowed before 09:19 AM. Current: ${timeStatus.timeStr}`,
        });
        return;
      }
      if (timeStatus.isAfter1515) {
        setLastOrderAlert({
          type: "error",
          msg: `[RULE VIOLATION] Entry blocked! Rule 2: No new entries allowed after 15:15 PM. Current: ${timeStatus.timeStr}`,
        });
        return;
      }
      if (timeStatus.isPast1525) {
        setLastOrderAlert({
          type: "error",
          msg: `[RULE VIOLATION] Order blocked! Rule 3: Intraday margin sq-off regime active after 15:25 PM. Current: ${timeStatus.timeStr}`,
        });
        return;
      }
    }

    const strikeToTrade = customStrike || atmStrike;
    let exactPremium = 100;
    if (dataSource === "replay") {
      exactPremium = type === "CE"
        ? (ceCandles.length > 0 ? ceCandles[ceCandles.length - 1].close : 100)
        : (peCandles.length > 0 ? peCandles[peCandles.length - 1].close : 90);
    } else {
      exactPremium = type === "CE"
        ? (engine.ceCandles.length > 0 ? engine.ceCandles[engine.ceCandles.length - 1].close : 100)
        : (engine.peCandles.length > 0 ? engine.peCandles[engine.peCandles.length - 1].close : 90);
    }

    if (customStrike) {
      const match = strikes.find((s) => s.strike === customStrike);
      if (match) {
        exactPremium = type === "CE" ? match.callPremium : match.putPremium;
      }
    }

    const premiumPrice = Math.round(exactPremium * 100) / 100;
    const marginNeeded = premiumPrice * tradeQuantity;

    if (side === "BUY" && accountBalance < marginNeeded) {
      setLastOrderAlert({
        type: "error",
        msg: `Insufficient margin! Required: ₹${marginNeeded.toFixed(2)}, Available: ₹${accountBalance.toFixed(2)}`,
      });
      return;
    }

    // Set stop loss and profit targets dynamically relative to Buy/Sell direction
    const computedSL = useSLTP
      ? (side === "BUY"
          ? Math.round(premiumPrice * (1 - slPercent / 100) * 100) / 100
          : Math.round(premiumPrice * (1 + slPercent / 100) * 100) / 100)
      : undefined;

    const computedTP = useSLTP
      ? (side === "BUY"
          ? Math.round(premiumPrice * (1 + tpPercent / 100) * 100) / 100
          : Math.round(premiumPrice * (1 - tpPercent / 100) * 100) / 100)
      : undefined;

    const orderId = Math.random().toString(36).substring(3, 9).toUpperCase();

    const newPosition: Position = {
      id: orderId,
      instrument,
      type,
      strike: strikeToTrade,
      entryPrice: premiumPrice,
      quantity: tradeQuantity,
      currentPrice: premiumPrice,
      stopLoss: computedSL,
      takeProfit: computedTP,
      pnl: 0,
      timestamp: new Date().toLocaleTimeString(),
      side,
      entrySpot: spotPrice,
      entryTimeSec: spotCandles[spotCandles.length - 1]?.time || Math.floor(Date.now() / 1000),
      status: "ACTIVE",
    };

    setPositions((prev) => [...prev, newPosition]);
    setTradeHistory((prev) => [...prev, newPosition]);

    if (side === "BUY") {
      setAccountBalance((prev) => prev - marginNeeded);
    } else {
      setAccountBalance((prev) => prev + marginNeeded);
    }

    setLastOrderAlert({
      type: "success",
      msg: `Executed: ${side === "BUY" ? "Bought" : "Sold (Write)"} ${instrument} ${strikeToTrade} ${type} at ₹${premiumPrice} x ${tradeQuantity} contracts.`,
    });

    // Publish Order Event to external Python Application to record buy/sell actions
    let baseApiUrl = "http://localhost:8000";
    try {
      const parsedUrl = new URL(pythonUrl);
      baseApiUrl = parsedUrl.origin;
    } catch (_err) {
      // safe fallback
    }
    const orderPostUrl = `${baseApiUrl}/api/order`;

    fetch(orderPostUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({
        orderId,
        side,
        type,
        strike: strikeToTrade,
        quantity: tradeQuantity,
        entryPrice: premiumPrice,
        timestamp: new Date().toLocaleTimeString(),
        instrument,
      }),
    }).catch((_e) => {
      // Safe discard on offline environment
    });
  };

  const executeBuyOrder = (type: "CE" | "PE", customStrike?: number) => {
    executeOrder("BUY", type, customStrike);
  };

  const triggerMarketExit = (posId: string, alertMsg?: string) => {
    const activePos = positions.find((p) => p.id === posId);
    if (!activePos) return;

    // Close transaction and return cash delta
    const closingPrice = activePos.currentPrice;
    const marginChange = closingPrice * activePos.quantity;

    if (activePos.side === "SELL") {
      setAccountBalance((bal) => bal - marginChange);
    } else {
      setAccountBalance((bal) => bal + marginChange);
    }

    setLastOrderAlert({
      type: "success",
      msg: alertMsg || `Closed Scalp Position of ${activePos.side || "BUY"} ${activePos.type} at ₹${closingPrice}. P&L realized: ₹${activePos.pnl.toFixed(2)}`,
    });

    setPositions((prev) => prev.filter((p) => p.id !== posId));

    setTradeHistory((prevHistory) =>
      prevHistory.map((h) => {
        if (h.id === posId) {
          return {
            ...h,
            status: "CLOSED",
            exitSpot: spotPrice,
            exitPrice: closingPrice,
            pnl: activePos.pnl,
            exitReason: alertMsg || "Manual Exit",
            exitTimeSec: spotCandles[spotCandles.length - 1]?.time || Math.floor(Date.now() / 1000),
          };
        }
        return h;
      })
    );

    // Also publish exit to Python API for real-time portfolio management Sync
    let baseApiUrl = "http://localhost:8000";
    try {
      const parsedUrl = new URL(pythonUrl);
      baseApiUrl = parsedUrl.origin;
    } catch (_err) {
      // safe fallback
    }
    const exitPostUrl = `${baseApiUrl}/api/order/exit`;
    fetch(exitPostUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({
        orderId: activePos.id,
        closingPrice,
        pnl: activePos.pnl,
        timestamp: new Date().toLocaleTimeString(),
      }),
    }).catch((_e) => {
      // safe discard
    });
  };

  const triggerCloseAll = () => {
    positions.forEach((pos) => {
      triggerMarketExit(pos.id, `Terminated multi-monitor order ${pos.id} at ₹${pos.currentPrice}`);
    });
  };

  // Helper stats for current visual portfolio
  const totalPnL = useMemo(() => {
    return positions.reduce((total, pos) => total + pos.pnl, 0);
  }, [positions]);

  const activeMarginInPlay = useMemo(() => {
    return positions.reduce((total, pos) => total + (pos.entryPrice * pos.quantity), 0);
  }, [positions]);

  // Market structure values calculated dynamically
  const mStructures = useMemo(() => {
    return engine.getMarketStructure();
  }, [spotCandles]);

  // Interactive zoom utilities on scroll/click
  const handleZoom = (amount: number) => {
    setViewportCandles((prev) => Math.max(10, Math.min(80, prev + amount)));
  };

  const displaySpotCandles = useMemo(() => {
    return spotCandles.slice(-viewportCandles);
  }, [spotCandles, viewportCandles]);

  const displayCECandles = useMemo(() => {
    return ceCandles.slice(-viewportCandles);
  }, [ceCandles, viewportCandles]);

  const displayPECandles = useMemo(() => {
    return peCandles.slice(-viewportCandles);
  }, [peCandles, viewportCandles]);

  return (
    <div id="day-trader-terminal" className="min-h-screen bg-[#07080a] text-zinc-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-black">
      {/* Dynamic Order Toast Notification Banner */}
      {lastOrderAlert && (
        <div
          id="alert-toast"
          className={`fixed top-4 right-4 z-50 rounded-xl px-4 py-3 shadow-2xl flex items-center gap-3 backdrop-blur-md max-w-md border animate-bounce ${
            lastOrderAlert.type === "success"
              ? "bg-[#0b1d12]/90 border-emerald-500/50 text-emerald-300"
              : "bg-[#251010]/95 border-rose-500/40 text-rose-300"
          }`}
        >
          <Zap className="h-5 w-5 flex-shrink-0 animate-pulse" />
          <div className="text-xs font-semibold">{lastOrderAlert.msg}</div>
          <button
            id="close-toast-btn"
            onClick={() => setLastOrderAlert(null)}
            className="ml-auto hover:bg-white/10 rounded p-1 text-zinc-400 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* TOP DECK HEADER STRIP (Concealable for space optimization) */}
      {!isCompactHeader && (
        <header id="terminal-header" className="bg-[#0b0c10] border-b border-zinc-800/80 px-4 py-2 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-emerald-500 flex items-center justify-center text-black font-extrabold shadow-lg shadow-emerald-500/20">
              <Activity className="h-4.5 w-4.5" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white flex items-center flex-wrap gap-2">
                DAY TRADER OPTIONS TERMINAL
                <span className="text-[10px] bg-zinc-800 text-zinc-400 border border-zinc-700 px-1.5 py-0.2 rounded font-mono font-medium">LIVE V1.0</span>
                {dataSource === "external" ? (
                  <span className="text-[10px] bg-purple-500/15 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded font-mono font-semibold flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
                    PYTHON API LINKED
                  </span>
                ) : dataSource === "replay" ? (
                  <span className="text-[10px] bg-purple-500/15 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded font-mono font-semibold flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
                    DUCKDB REPLAY ACTIVE
                  </span>
                ) : (
                  <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-mono font-medium flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    EMULATOR ACTIVE
                  </span>
                )}
              </h1>
              <p className="text-[10px] text-zinc-400">Institutional PCR Underlay & Market Structure Edge</p>
            </div>
          </div>

          {/* Global Stock Stats Panel */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Index Selector */}
            <div className="flex bg-zinc-900 border border-zinc-800 rounded-lg p-0.5">
              <button
                id="select-nifty"
                onClick={() => handleInstrumentChange(InstrumentType.NIFTY)}
                className={`px-3 py-1 rounded text-xs font-bold transition ${
                  instrument === InstrumentType.NIFTY
                    ? "bg-zinc-800 text-white shadow-sm"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                NIFTY 50
              </button>
              <button
                id="select-banknifty"
                onClick={() => handleInstrumentChange(InstrumentType.BANKNIFTY)}
                className={`px-3 py-1 rounded text-xs font-bold transition ${
                  instrument === InstrumentType.BANKNIFTY
                    ? "bg-zinc-800 text-white shadow-sm"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                BANKNIFTY
              </button>
            </div>

            {/* Expiry day lock toggle */}
            <button
              id="toggle-expiry"
              onClick={toggleExpiryDay}
              className={`px-3 py-1 border rounded-lg text-xs font-bold flex items-center gap-1.5 transition ${
                config.isExpiryDay
                  ? "bg-rose-950/40 border-rose-500 text-rose-300 shadow-lg shadow-rose-500/5"
                  : "bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              {config.isExpiryDay ? "Thursday Expiry Active" : "Standard Expiry"}
            </button>

            {/* Low latency speed controls */}
            <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-lg p-0.5 gap-1.5">
              <button
                id="toggle-play-simulation"
                onClick={() => setIsPlaying(!isPlaying)}
                title={isPlaying ? "Pause market walk" : "Resume tick generation"}
                className="p-1 text-zinc-400 hover:text-white rounded hover:bg-zinc-800"
              >
                {isPlaying ? <Pause className="h-3.5 w-3.5 text-amber-400" /> : <Play className="h-3.5 w-3.5 text-emerald-400" />}
              </button>

              <span className="text-[10px] text-zinc-500 font-mono select-none">SPEED</span>
              <select
                id="simulation-speed"
                value={config.speedMultiplier}
                onChange={(e) => setConfig((prev) => ({ ...prev, speedMultiplier: Number(e.target.value) }))}
                className="bg-zinc-950 text-white text-[10px] border-none focus:ring-0 py-0.5 px-1 font-mono rounded"
              >
                <option value="1">1x (Real)</option>
                <option value="2">2x Fast</option>
                <option value="5">5x Scalper</option>
              </select>
            </div>
          </div>

          {/* Real-time Ticker Strips */}
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="bg-zinc-900/60 px-3 py-1 rounded border border-zinc-800">
              <span className="text-zinc-500 mr-2 uppercase block text-[8px] text-zinc-500 font-bold">SPOT INDEX</span>
              <span className="text-emerald-400 font-bold tracking-wider">{spotPrice.toFixed(2)}</span>
            </div>

            <div className="bg-zinc-900/60 px-3 py-1 rounded border border-zinc-800">
              <span className="text-zinc-500 mr-2 uppercase block text-[8px] text-zinc-500 font-bold">ATM STRIKE</span>
              <span className="text-white font-bold">{atmStrike}</span>
            </div>

            <div className="bg-zinc-900/60 px-3 py-1 rounded border border-zinc-800 flex flex-col justify-center">
              <span className="text-zinc-500 uppercase text-[8px] text-zinc-500 font-bold mr-1">COI PCR</span>
              <span className={`font-bold px-1 rounded text-black text-center text-[10px] ${coiPcr > 1.2 ? "bg-emerald-500" : coiPcr < 0.8 ? "bg-rose-500" : "bg-zinc-700 text-white"}`}>
                {coiPcr.toFixed(2)}
              </span>
            </div>

            <div className="bg-zinc-900/60 px-3 py-1 rounded border border-zinc-800 flex flex-col justify-center text-center">
              <span className="text-zinc-500 uppercase text-[8px] text-zinc-500 font-bold">WINDOW</span>
              <span className={`text-[10px] rounded px-1.5 py-0.2 font-semibold ${
                windowStatus === "Aligned"
                  ? "bg-emerald-900/50 text-emerald-300"
                  : "bg-red-950/50 text-amber-300 animate-pulse"
                }`}
              >
                {windowStatus}
              </span>
            </div>
          </div>
        </header>
      )}

      {/* SUB HEADER NAV BAR */}
      <div id="sub-header" className="bg-[#0e1017] border-b border-zinc-800 px-4 py-1 flex justify-between items-center text-xs">
        <div className="flex gap-2 items-center">
          <button
            id="tab-terminal"
            onClick={() => setActiveTab("terminal")}
            className={`px-3 py-1.5 rounded font-bold transition flex items-center gap-1.5 ${
              activeTab === "terminal" ? "bg-emerald-500 text-black shadow" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Maximize2 className="h-3.5 w-3.5" />
            Scalper Dashboard
          </button>
          <button
            id="tab-pnl-analysis"
            onClick={() => setActiveTab("pnl_analysis")}
            className={`px-3 py-1.5 rounded font-bold transition flex items-center gap-1.5 ${
              activeTab === "pnl_analysis" ? "bg-amber-500 text-black shadow" : "text-amber-500/80 hover:text-white"
            }`}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            P&L & Performance Tab
          </button>
          <button
            id="tab-strategy"
            onClick={() => setActiveTab("strategy")}
            className={`px-3 py-1.5 rounded font-bold transition flex items-center gap-1.5 ${
              activeTab === "strategy" ? "bg-emerald-500 text-black shadow" : "text-zinc-400 hover:text-white"
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            Strategy Rules Check
          </button>
          <button
            id="tab-integration"
            onClick={() => setActiveTab("integration")}
            className={`px-3 py-1.5 rounded font-bold transition flex items-center gap-1.5 ${
              activeTab === "integration" ? "bg-purple-600 text-white shadow" : "bg-purple-950/10 text-purple-400 border border-purple-500/15 hover:text-purple-300"
            }`}
          >
            <Database className="h-3.5 w-3.5" />
            Python API Integration
          </button>

          {/* Quick Engine Telemetry Switcher */}
          <div className="flex bg-zinc-950 border border-zinc-800 rounded-lg p-0.5 ml-2.5">
            <button
              id="quick-set-emu"
              onClick={() => { setDataSource("simulation"); setIsPolling(false); }}
              title="Switch to Internal Low-latency Market Simulator"
              className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase transition flex items-center gap-1 cursor-pointer ${
                dataSource === "simulation"
                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                  : "text-zinc-500 hover:text-zinc-355"
              }`}
            >
              <RefreshCw className="h-3 w-3" />
              EMULATOR
            </button>
            <button
              id="quick-set-replay"
              onClick={() => { setDataSource("replay"); setIsPolling(false); }}
              title="Switch to High-Res DuckDB Historical Replay"
              className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase transition flex items-center gap-1 cursor-pointer ${
                dataSource === "replay"
                  ? "bg-amber-500/15 text-amber-400 border border-amber-500/25"
                  : "text-zinc-500 hover:text-zinc-355"
              }`}
            >
              <Database className="h-3 w-3" />
              REPLAY
            </button>
            <button
              id="quick-set-python"
              onClick={() => { setDataSource("external"); }}
              title="Switch to Local Python Server API quotes feed"
              className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase transition flex items-center gap-1 cursor-pointer ${
                dataSource === "external"
                  ? "bg-purple-500/15 text-purple-400 border border-purple-500/25"
                  : "text-zinc-500 hover:text-zinc-355"
              }`}
            >
              <Zap className="h-3 w-3" />
              PYTHON API
            </button>
          </div>

          {/* Compact metrics overlay shown only on compact header mode to save space */}
          {isCompactHeader && (
            <div className="hidden md:flex items-center gap-3 ml-4 pl-4 border-l border-zinc-800 text-[11px] font-mono select-none">
              <span className="text-zinc-400">SPOT: <strong className="text-emerald-400 font-extrabold">{spotPrice.toFixed(2)}</strong></span>
              <span className="text-zinc-400 text-[10px]">ATM: <strong className="text-zinc-200">{atmStrike}</strong></span>
              <span className="text-zinc-400 flex items-center gap-1 text-[10px]">
                PCR: <strong className={`px-1 rounded text-black font-extrabold ${
                  coiPcr > 1.2 ? "bg-emerald-500" : coiPcr < 0.8 ? "bg-rose-500" : "bg-zinc-700 text-white"
                }`}>{coiPcr.toFixed(2)}</strong>
              </span>
              <span className="text-zinc-400 text-[10px]">
                WINDOW: <strong className={windowStatus === "Aligned" ? "text-emerald-400" : "text-amber-400 animate-pulse"}>{windowStatus}</strong>
              </span>
              <span className="text-zinc-550 border border-zinc-800 px-1.5 py-0.2 rounded font-extrabold text-[9px] uppercase tracking-wider ml-1">
                {dataSource === "replay" ? selectedReplayFile.replace(".duckdb", "") : "LIVE"}
              </span>
            </div>
          )}
        </div>

        <div className="flex gap-4 items-center">
          <div className="text-zinc-500 text-[11px] selection:bg-zinc-800">
            DEMO ACCOUNT: <span className="font-bold text-zinc-300 font-mono">₹{accountBalance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
          </div>
          <button
            id="reset-demo-bal"
            onClick={() => {
              setAccountBalance(500000);
              setPositions([]);
              setLastOrderAlert({ type: "success", msg: "Demo balance reset to ₹5,00,000 INR." });
            }}
            title="Reset Balance Back to 5 Lakhs"
            className="hover:text-emerald-400 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>

          <button
            id="toggle-compact-header-state"
            onClick={() => setIsCompactHeader(!isCompactHeader)}
            className="flex items-center gap-1 px-2.5 py-1 bg-zinc-900 hover:bg-zinc-850 text-zinc-300 rounded-lg border border-zinc-850/80 hover:border-zinc-700 text-[10px] font-extrabold uppercase transition tracking-wider ctrl-header cursor-pointer active:scale-95"
          >
            {isCompactHeader ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
            {isCompactHeader ? "Full Header" : "Compact View"}
          </button>
        </div>
      </div>

      {activeTab === "pnl_analysis" ? (
        /* P&L & PERFORMANCE TAB */
        <div id="pnl-analysis-view" className="p-4 lg:p-6 max-w-7xl mx-auto overflow-y-auto flex-1 w-full space-y-6">

          {/* Header Dashboard section */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <TrendingUp className="h-5.5 w-5.5 text-amber-500" /> Options Scalping P&L & Performance Cabin
              </h2>
              <p className="text-xs text-zinc-400">Post-trade capital curve, win metrics, and rules compliance audit logs</p>
            </div>

            <button
              id="export-csv-performance-btn"
              onClick={handleExportCSV}
              className="bg-amber-500 hover:bg-amber-600 text-black px-4 py-2 rounded-xl text-xs font-black shadow-lg shadow-amber-500/10 flex items-center gap-1.5 transition self-start active:scale-95 cursor-pointer"
            >
              <FileText className="h-4 w-4" /> Export Session Trade Log (CSV)
            </button>
          </div>

          {/* KPI Analytics Cards row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total PnL Card */}
            <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl space-y-1">
              <span className="text-[10px] text-zinc-400 uppercase font-bold tracking-wider">Net Realized P&L</span>
              <div className={`text-xl font-black font-mono ${pnlStats.totalRealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {pnlStats.totalRealizedPnL >= 0 ? "+" : ""}₹{pnlStats.totalRealizedPnL.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <p className="text-[9px] text-zinc-500 font-mono">Realized from {pnlStats.closedCount} completed trades</p>
            </div>

            {/* Win Rate Card */}
            <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl space-y-1">
              <span className="text-[10px] text-zinc-400 uppercase font-bold tracking-wider">Win Rate Percentage</span>
              <div className="text-xl font-black font-mono text-zinc-200">
                {pnlStats.winRate.toFixed(1)}%
              </div>
              <div className="text-[9px] text-zinc-500 font-mono flex justify-between">
                <span>Wins: {pnlStats.winCount}</span>
                <span>Losses: {pnlStats.lossCount}</span>
              </div>
            </div>

            {/* Profit Factor Card */}
            <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl space-y-1">
              <span className="text-[10px] text-zinc-400 uppercase font-bold tracking-wider">Profit Factor (PF)</span>
              <div className="text-xl font-black font-mono text-zinc-200">
                {pnlStats.profitFactor === Infinity ? "∞" : pnlStats.profitFactor.toFixed(2)}
              </div>
              <p className="text-[9px] text-zinc-500 font-mono">Ratio of Win Capital / Loss Capital</p>
            </div>

            {/* Average Profit vs Loss Card */}
            <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-xl space-y-1">
              <span className="text-[10px] text-zinc-400 uppercase font-bold tracking-wider">Avg Win vs Avg Loss</span>
              <div className="text-sm font-bold font-mono text-zinc-200 flex flex-col justify-center">
                <span className="text-emerald-400">W: +₹{pnlStats.avgProfit.toFixed(1)}</span>
                <span className="text-rose-400">L: -₹{pnlStats.avgLoss.toFixed(1)}</span>
              </div>
            </div>
          </div>

          {/* Main Visual grid */}
          <div className="grid lg:grid-cols-12 gap-6">

            {/* Left Col: Capital Curve (8 Cols) */}
            <div className="lg:col-span-8 bg-zinc-900/40 border border-zinc-900 rounded-2xl p-5 space-y-4">

              {/* Dynamic SVG Chart render */}
              {pnlStats.pnlCurvePoints.length < 2 ? (
                <div className="h-64 flex flex-col items-center justify-center border border-zinc-800/40 border-dashed rounded-xl bg-zinc-950/20 text-xs text-zinc-500">
                  <TrendingUp className="h-10 w-10 text-zinc-700 mb-2 animate-pulse" />
                  No closed scalp actions recorded to model the equity path curve.
                  <span className="text-[10px] text-zinc-500 block mt-1">Deploy options capital in terminal to draw cumulative stats metrics.</span>
                </div>
              ) : (
                <div className="bg-[#0e1017]/80 rounded-xl border border-zinc-800/60 p-4">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-[11px] font-bold text-zinc-400 font-sans tracking-wide uppercase flex items-center gap-1.5">
                      <Activity className="h-3.5 w-3.5 text-amber-500" />
                      Intraday Scalper Capital Curve (₹5,00,000 Base)
                    </span>
                    <span className="text-[10px] font-mono text-amber-400 font-black">
                      VAL: ₹{(500000 + pnlStats.totalRealizedPnL).toLocaleString("en-IN")}
                    </span>
                  </div>

                  <div className="h-64 w-full relative pt-2">
                    <svg className="w-full h-full overflow-visible" viewBox="0 0 500 220" preserveAspectRatio="none">
                      {/* Zero horizontal baseline */}
                      <line x1="0" y1="110" x2="500" y2="110" stroke="#3f3f46" strokeWidth="0.8" strokeDasharray="4,4" />

                      {/* Helper horizontal grids */}
                      <line x1="0" y1="40" x2="500" y2="40" stroke="#18181b" strokeWidth="0.5" />
                      <line x1="0" y1="180" x2="500" y2="180" stroke="#18181b" strokeWidth="0.5" />

                      {(() => {
                        // Find cumulative sums for heights mapping
                        let sum = 0;
                        const cumSums = pnlStats.pnlCurvePoints.map(p => {
                          sum += p.pnl;
                          return sum;
                        });

                        const maxDev = Math.max(...cumSums.map(Math.abs), 500); // safety pad

                        const points = pnlStats.pnlCurvePoints.map((pt, i) => {
                          const x = (i / (pnlStats.pnlCurvePoints.length - 1)) * 500;
                          const y = 110 - (cumSums[i] / maxDev) * 90; // Fit safely to height
                          return `${x},${y}`;
                        });

                        const pointsStr = points.join(" ");
                        const isProfitable = pnlStats.totalRealizedPnL >= 0;

                        return (
                          <g>
                            {/* Area fill */}
                            <defs>
                              <linearGradient id="curveShade" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={isProfitable ? "#10b981" : "#f43f5e"} stopOpacity="0.18" />
                                <stop offset="100%" stopColor="#09090b" stopOpacity="0" />
                              </linearGradient>
                            </defs>

                            {points.length > 1 && (
                              <>
                                <path
                                  d={`M 0,110 L ${pointsStr} L 500,110 Z`}
                                  fill="url(#curveShade)"
                                />
                                <path
                                  d={`M ${pointsStr}`}
                                  fill="none"
                                  stroke={isProfitable ? "#10b981" : "#f43f5e"}
                                  strokeWidth="2.5"
                                  strokeLinecap="round"
                                />
                              </>
                            )}

                            {/* Circles with Tooltips */}
                            {points.map((pt, i) => {
                              const [cx, cy] = pt.split(",");
                              const singlePnL = pnlStats.pnlCurvePoints[i].pnl;
                              return (
                                <g key={`pt-dot-${i}`} className="group/circ">
                                  <circle
                                    cx={cx}
                                    cy={cy}
                                    r="4.5"
                                    fill={singlePnL >= 0 ? (i === 0 ? "#71717a" : "#10b981") : "#f43f5e"}
                                    stroke="#09090b"
                                    strokeWidth="1.5"
                                    className="transition-all duration-200 group-hover/circ:r-6"
                                  />
                                </g>
                              );
                            })}
                          </g>
                        );
                      })()}
                    </svg>
                  </div>

                  <div className="flex justify-between items-center mt-3 text-[10px] text-zinc-500 font-mono">
                    <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>Start balance: ₹5.0L</span>
                    <span>Equity curve drawn across {pnlStats.closedCount} trade segments</span>
                    <span className={pnlStats.totalRealizedPnL >= 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                      Net change: {pnlStats.totalRealizedPnL >= 0 ? "+" : ""}₹{pnlStats.totalRealizedPnL.toFixed(1)}
                    </span>
                  </div>
                </div>
              )}

              {/* CE vs PE Split analysis graph row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-900 flex flex-col justify-between">
                  <h4 className="text-xs font-bold text-zinc-300 mb-2 uppercase flex items-center gap-1.5">
                    <span className="w-1.5 h-3 bg-emerald-500 rounded"></span> CE Calls Trade Allocation
                  </h4>
                  <div className="space-y-2 font-mono">
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500">Total Contracts Traveled:</span>
                      <span className="text-zinc-100 font-bold">{pnlStats.ceCount} trades</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500">Realized P&L:</span>
                      <span className={`font-bold ${pnlStats.ceRealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {pnlStats.ceRealizedPnL >= 0 ? "+" : ""}₹{pnlStats.ceRealizedPnL.toFixed(2)}
                      </span>
                    </div>
                    {/* Progress Slider */}
                    <div className="w-full bg-zinc-900 rounded-full h-1.5 mt-2">
                      <div
                        className="bg-emerald-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${pnlStats.totalTrades > 0 ? (pnlStats.ceCount / pnlStats.totalTrades) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-900 flex flex-col justify-between">
                  <h4 className="text-xs font-bold text-zinc-300 mb-2 uppercase flex items-center gap-1.5">
                    <span className="w-1.5 h-3 bg-rose-500 rounded"></span> PE Puts Trade Allocation
                  </h4>
                  <div className="space-y-2 font-mono">
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500">Total Contracts Traveled:</span>
                      <span className="text-zinc-100 font-bold">{pnlStats.peCount} trades</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500">Realized P&L:</span>
                      <span className={`font-bold ${pnlStats.peRealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {pnlStats.peRealizedPnL >= 0 ? "+" : ""}₹{pnlStats.peRealizedPnL.toFixed(2)}
                      </span>
                    </div>
                    {/* Progress Slider */}
                    <div className="w-full bg-zinc-900 rounded-full h-1.5 mt-2">
                      <div
                        className="bg-rose-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${pnlStats.totalTrades > 0 ? (pnlStats.peCount / pnlStats.totalTrades) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

            </div>

            {/* Right Col: Rules Compliance scorecard and extreme performance (4 Cols) */}
            <div className="lg:col-span-4 space-y-6">

              {/* COMPLIANCE CARD */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4 space-y-4">
                <div className="border-b border-zinc-800 pb-2 mb-1">
                  <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                    <Sliders className="h-4 w-4 text-purple-400" /> Scalper Strategy Rule compliance
                  </h3>
                  <p className="text-[10px] text-zinc-500 uppercase font-mono mt-0.5">Real-time check on rules</p>
                </div>

                <div className="space-y-3.5 text-xs">
                  {/* Rule 1 item */}
                  <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-850 flex items-start gap-2.5">
                    <div className={`mt-0.5 p-1 rounded-md ${pnlStats.rule1Violations === 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-rose-400"}`}>
                      {pnlStats.rule1Violations === 0 ? (
                        <span className="text-[10px] font-extrabold leading-none">PASS</span>
                      ) : (
                        <span className="text-[10px] font-extrabold leading-none">WARN</span>
                      )}
                    </div>
                    <div className="flex-1 space-y-0.5">
                      <strong className="block text-zinc-200">Rule 1: No Trades before 09:19</strong>
                      <span className="text-[10px] text-zinc-500 block leading-tight">Indians morning open volatility safety protocol</span>
                      {pnlStats.rule1Violations > 0 && (
                        <span className="text-[10px] font-mono font-bold text-rose-400 bg-rose-950/20 px-1.5 py-0.2 rounded mt-1.5 inline-block">
                          {pnlStats.rule1Violations} early entries flagged! No trades allowed before 09:19.
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Rule 2 item */}
                  <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-850 flex items-start gap-2.5">
                    <div className={`mt-0.5 p-1 rounded-md ${pnlStats.rule2Violations === 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-rose-400"}`}>
                      {pnlStats.rule2Violations === 0 ? (
                        <span className="text-[10px] font-extrabold leading-none">PASS</span>
                      ) : (
                        <span className="text-[10px] font-extrabold leading-none">WARN</span>
                      )}
                    </div>
                    <div className="flex-1 space-y-0.5">
                      <strong className="block text-zinc-200">Rule 2: No New Entries after 15:15</strong>
                      <span className="text-[10px] text-zinc-500 block leading-tight">Avoid intraday broker square-offs & high-spread premium drops</span>
                      {pnlStats.rule2Violations > 0 && (
                        <span className="text-[10px] font-mono font-bold text-rose-400 bg-rose-950/20 px-1.5 py-0.2 rounded mt-1.5 inline-block">
                          {pnlStats.rule2Violations} late entries triggered after 15:15.
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Rule 3 item */}
                  <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-850 flex items-start gap-2.5">
                    <div className={`mt-0.5 p-1 rounded-md ${pnlStats.rule3Violations === 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400 animate-pulse"}`}>
                      {pnlStats.rule3Violations === 0 ? (
                        <span className="text-[10px] font-extrabold leading-none">PASS</span>
                      ) : (
                        <span className="text-[10px] font-extrabold leading-none">WARN</span>
                      )}
                    </div>
                    <div className="flex-1 space-y-0.5">
                      <strong className="block text-zinc-200">Rule 3: Live Position Auto Close @ 15:25</strong>
                      <span className="text-[10px] text-zinc-500 block leading-tight">Liquidate overnight risks. Zero overnight carrying allowed.</span>
                      {pnlStats.rule3Violations > 0 && (
                        <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-950/20 px-1.5 py-0.2 rounded mt-1.5 inline-block">
                          {pnlStats.rule3Violations} auto close actions triggered past 15:25 safely!
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="pt-2">
                  <div className="text-[10px] bg-[#0e2c1c]/10 text-emerald-400 p-2.5 rounded-lg border border-emerald-500/15 flex items-center gap-1.5">
                    <span className="font-extrabold block">Compliance Index:</span>
                    <span className="font-mono text-white text-xs font-black">
                      {Math.max(0, 100 - (pnlStats.rule1Violations + pnlStats.rule2Violations) * 20)}% Compliance
                    </span>
                  </div>
                </div>
              </div>

              {/* Historical statistics breakdown */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4 space-y-2">
                <h3 className="text-xs font-bold text-zinc-100 uppercase tracking-wide">Extreme Scalp Achievements</h3>
                <div className="divide-y divide-zinc-850 text-[11px] font-mono pt-1">
                  <div className="flex justify-between py-2 text-zinc-400">
                    <span>Largest Scalped Win:</span>
                    <span className="text-emerald-400 font-bold">+₹{pnlStats.largestWin.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between py-2 text-zinc-400">
                    <span>Largest Scalped Loss:</span>
                    <span className="text-rose-400 font-bold">-₹{pnlStats.largestLoss.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between py-2 text-zinc-400">
                    <span>Win Rate Success:</span>
                    <span className="text-zinc-200">{pnlStats.winCount} wins out of {pnlStats.closedCount} completed scalps</span>
                  </div>
                </div>
              </div>

            </div>

          </div>

          {/* Table of closed trades */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Completed Trades Master Log ({pnlStats.closedCount})</span>
              <span className="text-[10px] text-zinc-400 font-mono">Real-time compilation</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-zinc-850 text-zinc-400 text-[10px] uppercase font-mono">
                    <th className="py-2.5">Trade ID</th>
                    <th>Type</th>
                    <th>Strike</th>
                    <th>Side</th>
                    <th>Qty</th>
                    <th>Entry & Exit Price</th>
                    <th>Realized PnL</th>
                    <th>Reason</th>
                    <th>Timing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 font-mono">
                  {tradeHistory.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="text-center py-6 text-zinc-500 text-xs font-sans leading-relaxed">
                        No transactions registered yet. Switch to terminal and start scaling call/put positions.
                      </td>
                    </tr>
                  ) : (
                    tradeHistory.map((t) => (
                      <tr key={`log-table-row-${t.id}`} className="hover:bg-zinc-950/40 text-zinc-300">
                        <td className="py-3 font-bold text-amber-500">{t.id}</td>
                        <td>
                          {t.type === "CE" ? (
                            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1 rounded text-[10px] font-black">CE</span>
                          ) : (
                            <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-1 rounded text-[10px] font-black">PE</span>
                          )}
                        </td>
                        <td>{t.strike}</td>
                        <td className="text-[10px] font-black text-zinc-450">{t.side || "BUY"}</td>
                        <td>{t.quantity}</td>
                        <td>
                          <span>₹{t.entryPrice.toFixed(1)}</span>
                          <span className="text-zinc-500 px-1">→</span>
                          <span>{t.exitPrice ? `₹${t.exitPrice.toFixed(1)}` : `₹${t.currentPrice.toFixed(1)}`}</span>
                        </td>
                        <td className={t.pnl >= 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                          {t.pnl >= 0 ? "+" : ""}₹{t.pnl.toFixed(1)}
                        </td>
                        <td className="text-[10px] font-sans text-zinc-400 max-w-xs truncate">{t.exitReason || (t.status === "ACTIVE" ? "Position Open" : "Manual Exit")}</td>
                        <td className="text-[10px] text-zinc-500">
                          {t.timestamp} {t.exitTimeSec ? `| ${new Date(t.exitTimeSec * 1000).toLocaleTimeString()}` : ""}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      ) : activeTab === "strategy" ? (
        /* STRATEGY GUIDE TAB */
        <div id="strategy-details-view" className="p-6 max-w-4xl mx-auto overflow-y-auto flex-1">
          <div className="bg-zinc-900/90 rounded-2xl p-6 border border-zinc-800 space-y-6">
            <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
              <Layers className="h-6 w-6 text-emerald-400" />
              <div>
                <h2 className="text-lg font-bold text-white">Consolidated Options Strategy Rules</h2>
                <p className="text-xs text-zinc-400">MD Documentation parameters integrated natively</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6 text-xs text-zinc-300">
              <div className="space-y-3 bg-black/40 p-4 rounded-xl border border-zinc-800/60">
                <h3 className="font-bold text-emerald-400 text-sm flex items-center gap-1">
                  <TrendingUp className="h-4 w-4" /> 1. COI PCR Calculations
                </h3>
                <p>Calculates dynamic Changes in Open Interest over 7 strikes (ATM and ±3 strikes).</p>
                <ul className="list-disc list-inside space-y-1.5 mt-2 text-zinc-400">
                  <li>NIFTY option strikes scale at exactly 50 point gaps</li>
                  <li>BANKNIFTY option strikes scale at 100 point gaps</li>
                  <li>Dynamic ATM Midpoint shifts locks 15s to stabilize window</li>
                  <li>Standard Bullish trigger holds at <strong className="text-white">COI PCR &gt; 1.2</strong></li>
                  <li>Standard Bearish trigger holds at <strong className="text-white">COI PCR &lt; 0.8</strong></li>
                </ul>
              </div>

              <div className="space-y-3 bg-black/40 p-4 rounded-xl border border-zinc-800/60">
                <h3 className="font-bold text-rose-400 text-sm flex items-center gap-1">
                  <Sliders className="h-4 w-4" /> 2. 3-Layer Confluence Engine
                </h3>
                <p>No trade entries occur unless all three institutional parameters line up perfectly:</p>
                <div className="space-y-2 mt-2 text-zinc-400">
                  <div>
                    <span className="text-zinc-200 font-semibold block">Layer A: Spot Market Structure</span>
                    Provides swing point validations such as structural Higher Highs or Lower Lows.
                  </div>
                  <div>
                    <span className="text-zinc-200 font-semibold block">Layer B: Options Premium Swings</span>
                    Ensures target option contract (CE or PE respectively) breaks above active morning premium records.
                  </div>
                  <div>
                    <span className="text-zinc-200 font-semibold block">Layer C: Absolute Volume & OI Walls Range</span>
                    Spots heavy writer barriers to identify peak retest support/resistance pivots.
                  </div>
                </div>
              </div>

              <div className="space-y-3 bg-black/40 p-4 rounded-xl border border-zinc-800/60">
                <h3 className="font-bold text-amber-400 text-sm flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4" /> 3. Expiry Day Protocols (Thursdays)
                </h3>
                <p>Boundary filters dynamically expand on expiry day to avoid fake institutional closures of standard hedges:</p>
                <ul className="list-disc list-inside space-y-1 mt-2 text-zinc-400">
                  <li>Bullish Scalp threshold expands upward to <strong className="text-white">1.40</strong></li>
                  <li>Bearish Scalp threshold compresses downward to <strong className="text-white">0.60</strong></li>
                  <li>Post 1:30 PM on Thursdays triggers a full <strong className="text-rose-400">GAMMA LOCK</strong> where directions are ignored.</li>
                </ul>
              </div>

              <div className="space-y-3 bg-black/40 p-4 rounded-xl border border-zinc-800/60">
                <h3 className="font-bold text-emerald-400 text-sm flex items-center gap-1">
                  <Target className="h-4 w-4" /> 4. Low-latency Executions
                </h3>
                <p>Option contract scalp management utilizes dedicated 1-minute 9 EMA execution lines.</p>
                <ul className="list-disc list-inside space-y-1 mt-2 text-zinc-400">
                  <li>Do not purchase option longs if price is beneath its 1-minute 9 EMA trailing support</li>
                  <li>Instantly exit all options positions if dynamic retailer traps are signaled</li>
                </ul>
              </div>
            </div>

            <div className="bg-emerald-950/10 border border-emerald-500/20 p-4 rounded-xl text-xs text-emerald-300">
              <strong className="block text-emerald-400 mb-1">Live Integration Ready:</strong>
              The backend logic written on <code className="bg-black/50 px-1 rounded">marketEngine.ts</code> tracks price actions and shifts metrics continuously. Switch back to the Scalper Dashboard to execute and watch live signals.
            </div>
          </div>
        </div>
      ) : activeTab === "integration" ? (
        /* PYTHON API INTEGRATION CENTER */
        <div id="integration-panel-view" className="p-4 lg:p-6 max-w-7xl mx-auto overflow-y-auto flex-1 w-full space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-805 pb-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                <Database className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Python API & Data Ingestion Center</h2>
                <p className="text-xs text-zinc-400">Bridge local automated quantitative models directly into the visual trade monitor</p>
              </div>
            </div>

            {/* Source Mode Toggle Card */}
            <div className="flex bg-zinc-900/90 border border-zinc-800 p-1 rounded-xl">
              <button
                id="select-src-sim"
                onClick={() => {
                  setDataSource("simulation");
                  setIsPolling(false);
                }}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                  dataSource === "simulation"
                    ? "bg-emerald-600 text-white shadow-md shadow-emerald-500/10"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Local Emulator
              </button>
              <button
                id="select-src-ext"
                onClick={() => setDataSource("external")}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                  dataSource === "external"
                    ? "bg-purple-600 text-white shadow-md shadow-purple-500/10"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                <Zap className="h-3.5 w-3.5" />
                External Python Feed
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* LEFT SIDE: CONFIG & INJECTOR (5 COLUMNS) */}
            <div className="lg:col-span-5 space-y-5">
              {/* Card 1: Live Server Polling Parameters */}
              <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-4">
                <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-purple-500" />
                  1. Live Network Ingestion setup
                </h3>

                <div className="space-y-3 pt-1 text-xs">
                  <div>
                    <label className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block mb-1">Target Python App URL</label>
                    <input
                      id="input-python-url"
                      type="text"
                      className="w-full bg-zinc-950 border border-zinc-800 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 rounded-lg px-3 py-2 text-zinc-200 font-mono text-xs"
                      value={pythonUrl}
                      onChange={(e) => setPythonUrl(e.target.value)}
                      placeholder="http://localhost:8000/api/quotes"
                    />
                    <p className="text-[10px] text-zinc-500 mt-1">
                      Localhost address running your quant execution backend (e.g. FastAPI on default port 8000).
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block mb-1 font-semibold">Polling Rate</label>
                      <select
                        id="select-polling-interval"
                        className="w-full bg-zinc-950 border border-zinc-800 focus:border-purple-500 font-mono rounded-lg px-2.5 py-1.5 text-zinc-300 text-xs"
                        value={pollingInterval}
                        onChange={(e) => setPollingInterval(Number(e.target.value))}
                      >
                        <option value="1">Every 1 Sec (Realtime)</option>
                        <option value="2">Every 2 Secs</option>
                        <option value="5">Every 5 Secs</option>
                        <option value="10">Every 10 Secs</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block mb-1 font-semibold">CORS Protocol</label>
                      <div className="bg-[#12141c] border border-purple-950/40 rounded-lg text-purple-300 px-3 py-2 text-[10px] text-center">
                        CORS Required (*)
                      </div>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      id="btn-toggle-polling"
                      onClick={() => {
                        if (dataSource !== "external") {
                          setDataSource("external");
                        }
                        setIsPolling(!isPolling);
                      }}
                      className={`w-full py-2 px-4 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 ${
                        isPolling
                          ? "bg-amber-600 text-white hover:bg-amber-500"
                          : "bg-purple-600 text-white hover:bg-purple-500 shadow-md shadow-purple-600/10"
                      }`}
                    >
                      {isPolling ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                      {isPolling ? "DEACTIVATE LIVE POLLING" : "START HTTP POLLING WORKER"}
                    </button>
                  </div>
                </div>

                {/* Polling Ingestion Diagnostics Panel */}
                <div className="bg-zinc-950 rounded-xl p-3 border border-zinc-800 mt-2 space-y-1.5 text-[11px] font-mono">
                  <div className="flex justify-between items-center pb-1 border-b border-zinc-900 text-zinc-500 text-[10px]">
                    <span>STATUS TERMINAL DIAGNOSTIC REPORT</span>
                    <span className="text-zinc-650">v1.1</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Pipeline Bridge:</span>
                    <span className={`font-semibold ${dataSource === "external" ? "text-purple-400" : "text-zinc-450"}`}>
                      {dataSource === "external" ? "EXTERNAL PYTHON" : "LOCAL EMULATOR"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Polling Status:</span>
                    <span className={`font-semibold flex items-center gap-1 ${
                      apiStatus === "connected" ? "text-emerald-400" :
                      apiStatus === "fetching" ? "text-purple-400" :
                      apiStatus === "error" ? "text-rose-400" : "text-zinc-400"
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        apiStatus === "connected" ? "bg-emerald-400 animate-ping" :
                        apiStatus === "fetching" ? "bg-purple-400" :
                        apiStatus === "error" ? "bg-rose-400" : "bg-zinc-400"
                      }`} />
                      {apiStatus === "connected" && "CONNECTED & REFRESHING"}
                      {apiStatus === "fetching" && "FETCHING PAYLOAD..."}
                      {apiStatus === "error" && "OFFLINE / CORRUPT DATA"}
                      {apiStatus === "idle" && "IDLE"}
                    </span>
                  </div>
                  {lastFeedTimestamp && (
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Last Sync Tick:</span>
                      <span className="text-zinc-200">{lastFeedTimestamp} (Local Time)</span>
                    </div>
                  )}
                  {apiError && (
                    <div className="bg-[#1c1212] border border-rose-950/40 p-2 rounded-lg text-rose-400 text-[10px] mt-2 whitespace-normal break-all">
                      <strong className="block mb-0.5">Connection Error:</strong>
                      {apiError}
                      <p className="mt-1 text-zinc-400 text-[9px] leading-relaxed">
                        Ensure your Python app is running on port 8000 and exposes CORS permissions.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Card 2: Direct Manual Payload Ingestion Terminal */}
              <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3 flex flex-col">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    2. Manual JSON Payload Injector
                  </h3>

                  {/* Preset Injectors */}
                  <div className="flex gap-1">
                    <button
                      id="btn-preset-bullish"
                      onClick={() => loadTestingPreset("bullish")}
                      className="text-[9px] bg-zinc-800 text-zinc-300 hover:text-emerald-400 hover:bg-zinc-850 px-2 py-0.5 rounded border border-zinc-700 transition font-bold"
                    >
                      Bullish Preset
                    </button>
                    <button
                      id="btn-preset-bearish"
                      onClick={() => loadTestingPreset("bearish")}
                      className="text-[9px] bg-zinc-800 text-zinc-300 hover:text-rose-400 hover:bg-zinc-850 px-2 py-0.5 rounded border border-zinc-700 transition font-bold"
                    >
                      Bearish Preset
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5 flex-1 flex flex-col">
                  <label className="text-[10px] text-zinc-400 font-mono block">Direct Paste Option Chain JSON Data</label>
                  <textarea
                    id="textarea-json-payload"
                    className="w-full h-64 bg-zinc-950 text-zinc-350 rounded-lg p-2.5 font-mono text-[10px] leading-relaxed border border-zinc-800 focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none flex-1 font-semibold"
                    value={manualPayloadText}
                    onChange={(e) => setManualPayloadText(e.target.value)}
                  />
                </div>

                <button
                  id="btn-inject-manual-json"
                  onClick={handleManualPayloadInject}
                  className="w-full bg-[#124e3c] hover:bg-[#155e49] text-emerald-350 border border-emerald-500/25 rounded-xl py-2 px-4 text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Zap className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
                  INJECT & RECALCULATE GRAPHICS INSTANTLY
                </button>
                <span className="text-[9px] text-zinc-500 text-center font-mono self-center">
                  This loads the pasted payload and automatically flips data mode to "External Python Feed".
                </span>
              </div>
            </div>

            {/* RIGHT SIDE: INTERFACE DOCUMENTATION & CODES (7 COLUMNS) */}
            <div className="lg:col-span-7 space-y-5">
              <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-5 space-y-6 overflow-y-auto">
                <div className="flex items-center gap-2 pb-3 border-b border-zinc-800">
                  <Layers className="h-5 w-5 text-purple-400" />
                  <div>
                    <h3 className="text-base font-bold text-white leading-none">Descriptive Integration Guidelines</h3>
                    <p className="text-xs text-zinc-400 mt-1">Expose a clean REST endpoint and stream your live indices / options chains</p>
                  </div>
                </div>

                {/* Sub-section A: JSON payload specification standard */}
                <div className="space-y-2 text-xs">
                  <h4 className="font-bold text-purple-400 uppercase tracking-widest text-[10px] font-mono">
                    I. Schema Specification dictionary
                  </h4>
                  <p className="text-zinc-300 leading-relaxed">
                    The options workspace processes single structured snapshot responses. Ensure your python web application returns the following schema exactly:
                  </p>

                  {/* JSON Schema visual explanation */}
                  <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-850 space-y-3 font-mono text-[10.5px]">
                    <div className="grid grid-cols-3 border-b border-zinc-900 pb-1.5 font-bold text-zinc-400">
                      <span>KEY PARAMETER</span>
                      <span>DATA TYPE</span>
                      <span>FUNCTION DETAILS</span>
                    </div>
                    <div className="grid grid-cols-3 border-b border-zinc-800/40 pb-1">
                      <span className="text-purple-400 font-bold">"spotPrice"</span>
                      <span className="text-amber-400">Float</span>
                      <span className="text-zinc-400 text-[10px]">Underlying index price (e.g. 22485.5)</span>
                    </div>
                    <div className="grid grid-cols-3 border-b border-zinc-800/40 pb-1">
                      <span className="text-purple-400 font-bold">"instrument"</span>
                      <span className="text-zinc-300">String</span>
                      <span className="text-zinc-500 text-[10px]">Either "NIFTY" or "BANKNIFTY"</span>
                    </div>
                    <div className="grid grid-cols-3 pb-1">
                      <span className="text-purple-400 font-bold">"strikeChain"</span>
                      <span className="text-blue-350 font-semibold">List [Dict]</span>
                      <span className="text-zinc-400 text-[10px]">Must contain exactly 7 strikes around ATM</span>
                    </div>
                  </div>

                  {/* Detailed child fields */}
                  <p className="text-[11px] text-zinc-400 leading-relaxed italic pt-1">
                    Each item in the <code className="bg-black/50 px-1 rounded text-purple-400">strikeChain</code> list must hold metrics: <code className="text-zinc-200">strike</code>, <code className="text-zinc-200">callOI</code> / <code className="text-zinc-200">putOI</code> (Absolute Open Interest size), <code className="text-zinc-300">callCOI</code> / <code className="text-zinc-300">putCOI</code> (Current Session Net Change in OI), and <code className="text-emerald-400 font-semibold">callPremium</code> / <code className="text-rose-300">putPremium</code> (Option last traded price).
                  </p>
                </div>

                {/* Sub-section B: Modern FastAPI Copyable Code Template */}
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center bg-purple-950/20 border border-purple-800/40 p-2.5 rounded-lg mb-1">
                    <div>
                      <h4 className="font-bold text-purple-300 uppercase tracking-widest text-[10px] font-mono">
                        II. FastAPI copy-paste backend boilerplate
                      </h4>
                      <p className="text-[10px] text-zinc-400 mt-0.5">High performance Async Server with native CORS setup</p>
                    </div>
                    <span className="text-[9px] bg-purple-900/35 text-purple-350 px-1.5 py-0.5 rounded font-mono font-bold">Port 8000</span>
                  </div>

                  <p className="text-zinc-300 leading-relaxed">
                    Here is a complete quantitative server script written in Python using <strong>FastAPI</strong> and <strong>uvicorn</strong>. Copy-paste this to expose your options indices data:
                  </p>

                  <div className="bg-zinc-950 border border-zinc-800 p-4 rounded-xl overflow-x-auto text-[10px] font-mono leading-relaxed text-zinc-300 max-h-80">
                    <pre id="code-block-fastapi" className="text-zinc-400 select-all">
{`from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random

app = FastAPI(title="Quant Options Pipeline Server")

# CRITICAL CORS: Allow cross-origin AJAX fetches from AI Studio Dev Terminal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits UI iframe connections (CORS bypass)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/quotes")
def get_custom_option_quotes():
    """
    Day Trader Options Terminal expects 7 strikes centered on ATM
    """
    # Simulate a dynamic spot level with random noise walk
    live_spot = 22485.50 + random.uniform(-15.0, 15.0)

    # Calculate ATM Strike base at 50 point steps for Nifty
    atm_strike = round(live_spot / 50) * 50

    # Structure 7 strikes centering surrounding the ATM Strike
    strikes = [atm_strike - 150, atm_strike - 100, atm_strike - 50, atm_strike, atm_strike + 50, atm_strike + 100, atm_strike + 150]

    options_chain = []
    for s in strikes:
        distance = live_spot - s
        options_chain.append({
            "strike": s,
            # Bullish writing if spot exceeds strike, bearish writing if spot drops
            "callOI": int(52000 + random.randint(-5000, 15000) if s >= atm_strike else 18000),
            "callCOI": int(random.randint(2000, 10000)),
            "callVolume": int(35000 + random.randint(0, 90000)),
            "callPremium": round(max(5.0, 110.0 + (distance * 0.7) + random.uniform(-2.0, 2.0)), 2),

            "putOI": int(68000 + random.randint(-3000, 22000) if s <= atm_strike else 9500),
            "putCOI": int(random.randint(3000, 12000)),
            "putVolume": int(28000 + random.randint(0, 80000)),
            "putPremium": round(max(5.0, 95.0 - (distance * 0.6) + random.uniform(-2.0, 2.0)), 2)
        })

    return {
        "spotPrice": round(live_spot, 2),
        "instrument": "NIFTY",
        "strikeChain": options_chain
    }

if __name__ == "__main__":
    # Start server locally on Port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)`}
                    </pre>
                  </div>
                </div>

                {/* Sub-section C: Flask Alternative Copyable Code Template */}
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center bg-blue-950/20 border border-blue-800/40 p-2.5 rounded-lg mb-1">
                    <div>
                      <h4 className="font-bold text-blue-300 uppercase tracking-widest text-[10px] font-mono">
                        III. Python Flask + CORS setup template
                      </h4>
                      <p className="text-[10px] text-zinc-400 mt-0.5">Alternative WSGI app template with Flask-CORS middleware</p>
                    </div>
                    <span className="text-[9px] bg-blue-900/40 text-blue-300 px-1.5 py-0.5 rounded font-mono font-bold">Port 8000</span>
                  </div>

                  <div className="bg-zinc-950 border border-zinc-800 p-4 rounded-xl overflow-x-auto text-[10px] font-mono leading-relaxed text-zinc-300 max-h-64">
                    <pre id="code-block-flask" className="text-zinc-400 select-all">
{`from flask import Flask, jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
# Enable CORS globally for all endpoints to bypass browser constraints
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/api/quotes", methods=["GET"])
def get_quotes_flask():
    spot = 22460.50 + random.uniform(-10, 10)

    return jsonify({
        "spotPrice": round(spot, 2),
        "instrument": "NIFTY",
        "strikeChain": [
            { "strike": 22300, "callOI": 15000, "callCOI": 2300, "callPremium": 185.2, "putOI": 42000, "putCOI": 5600, "putPremium": 15.2, "callVolume": 25000, "putVolume": 10000 },
            { "strike": 22350, "callOI": 21000, "callCOI": 4200, "callPremium": 142.0, "putOI": 31000, "putCOI": 4050, "putPremium": 23.5, "callVolume": 31000, "putVolume": 12000 },
            { "strike": 22400, "callOI": 32000, "callCOI": 6800, "callPremium": 105.4, "putOI": 25000, "putCOI": 3800, "putPremium": 36.1, "callVolume": 45000, "putVolume": 19000 },
            { "strike": 22450, "callOI": 41000, "callCOI": 9200, "callPremium": 75.8, "putOI": 18000, "putCOI": 2100, "putPremium": 55.4, "callVolume": 58000, "putVolume": 31000 },
            { "strike": 22500, "callOI": 59000, "callCOI": 12400, "callPremium": 51.5, "putOI": 11000, "putCOI": -800, "putPremium": 82.1, "callVolume": 89000, "putVolume": 12000 },
            { "strike": 22550, "callOI": 48000, "callCOI": 8100, "callPremium": 33.2, "putOI": 6000, "putCOI: ": -500, "putPremium": 110.2, "callVolume": 71000, "putVolume": 5500 },
            { "strike": 22600, "callOI": 36000, "callCOI": 5400, "callPremium": 19.5, "putOI": 2000, "putCOI": 0, "putPremium": 149.0, "callVolume": 46000, "putVolume": 1500 }
        ]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)`}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* CORE SCALPER WORKSPACE LAYOUT */
        <main id="scalper-workspace" className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-1.5 p-1.5">
          {/* COLUMN 1: SIDEBAR CONTROLS & TRADES (3 cols) */}
          <section id="sidebar-panel" className="lg:col-span-3 bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-3 flex flex-col justify-between overflow-y-auto space-y-3">
            <div>
              {/* Lot Selector Block */}
              <div className="border-b border-zinc-800/80 pb-3 mb-3">
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-[10px] text-zinc-400 font-bold tracking-wide uppercase">Scalp Quantity Size</label>
                  <span className="text-[10px] text-zinc-500 font-mono">Lot size: {instrument === InstrumentType.NIFTY ? "50" : "25"}</span>
                </div>
                <div className="grid grid-cols-4 gap-1">
                  {(() => {
                    const lotBase = instrument === InstrumentType.NIFTY ? 50 : 25;
                    return [lotBase, lotBase * 2, lotBase * 4, lotBase * 10].map((qty) => (
                      <button
                        id={`qty-set-${qty}`}
                        key={qty}
                        onClick={() => setTradeQuantity(qty)}
                        className={`py-1.5 rounded-lg text-xs font-mono font-bold border transition ${
                          tradeQuantity === qty
                            ? "bg-zinc-800 text-emerald-400 border-zinc-600 shadow"
                            : "bg-zinc-900 text-zinc-400 border-zinc-850 hover:bg-zinc-800/60"
                        }`}
                      >
                        {qty}
                      </button>
                    ));
                  })()}
                </div>
                {(() => {
                  const stepSize = instrument === InstrumentType.NIFTY ? 50 : 25;
                  return (
                    <div className="flex gap-2.5 mt-2">
                      <button
                        id="qty-decrement"
                        onClick={() => setTradeQuantity((q) => Math.max(stepSize, q - stepSize))}
                        className="flex-1 bg-zinc-900 border border-zinc-800 text-zinc-300 rounded py-1 flex items-center justify-center hover:bg-zinc-800 text-[10px] font-bold gap-1 transition"
                      >
                        <Minus className="h-2.5 w-2.5" /> {stepSize} Qty
                      </button>
                      <button
                        id="qty-increment"
                        onClick={() => setTradeQuantity((q) => q + stepSize)}
                        className="flex-1 bg-zinc-900 border border-zinc-800 text-zinc-300 rounded py-1 flex items-center justify-center hover:bg-zinc-800 text-[10px] font-bold gap-1 transition"
                      >
                        <Plus className="h-2.5 w-2.5" /> {stepSize} Qty
                      </button>
                    </div>
                  );
                })()}
              </div>

              {/* Instant One-Click Execution Panel */}
              <div className="border-b border-zinc-800/80 pb-3 mb-3 space-y-2.5">
                <div className="flex justify-between items-center">
                  <h3 className="text-[10px] text-zinc-400 font-bold uppercase tracking-wide flex items-center gap-1.5">
                    <Zap className="h-3 text-emerald-400 animate-pulse" /> One-Click Scalper (ATM Option)
                  </h3>
                  <div className="flex items-center gap-1">
                    <span className="text-[9px] text-zinc-500">Fast Keys</span>
                    <div className="bg-zinc-850 px-1 py-0.2 rounded border border-zinc-800 text-[9px] text-zinc-400 font-mono">ON</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {/* BUY CE CALL */}
                  <button
                    id="oneclick-buy-ce"
                    onClick={() => executeBuyOrder("CE")}
                    className="bg-emerald-500 hover:bg-emerald-600 text-black py-3 rounded-xl font-black text-xs flex flex-col items-center justify-center transition shadow-lg shadow-emerald-500/10 active:scale-95 cursor-pointer"
                  >
                    <span className="text-[9px] font-bold uppercase opacity-85">BUY CE INSTANT</span>
                    <span className="text-sm font-black font-mono tracking-wide">₹{ceCandles[ceCandles.length - 1]?.close.toFixed(1)}</span>
                  </button>

                  {/* BUY PE PUT */}
                  <button
                    id="oneclick-buy-pe"
                    onClick={() => executeBuyOrder("PE")}
                    className="bg-rose-500 hover:bg-rose-600 text-white py-3 rounded-xl font-black text-xs flex flex-col items-center justify-center transition shadow-lg shadow-rose-500/10 active:scale-95 cursor-pointer"
                  >
                    <span className="text-[9px] font-bold uppercase opacity-85">BUY PE INSTANT</span>
                    <span className="text-sm font-black font-mono tracking-wide">₹{peCandles[peCandles.length - 1]?.close.toFixed(1)}</span>
                  </button>
                </div>

                {/* SL / TP Config limits bar */}
                <div className="bg-zinc-900/60 p-2 rounded-lg border border-zinc-800 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-zinc-400 font-bold flex items-center gap-1">
                      <Target className="h-3 w-3 text-amber-400" /> Dynamic Stop & Target Targets
                    </span>
                    <input
                      id="toggle-sltp"
                      type="checkbox"
                      checked={useSLTP}
                      onChange={(e) => setUseSLTP(e.target.checked)}
                      className="rounded border-zinc-800 bg-zinc-950 text-emerald-500 focus:ring-0 cursor-pointer text-xs"
                    />
                  </div>

                  {useSLTP && (
                    <div className="space-y-2 pt-1 border-t border-zinc-800/80">
                      <div className="flex justify-between text-[10px] text-zinc-400">
                        <span>Stop Loss (SL)</span>
                        <span className="font-mono text-zinc-200">{slPercent}%</span>
                      </div>
                      <input
                        id="sl-percent-ranger"
                        type="range"
                        min="5"
                        max="30"
                        value={slPercent}
                        onChange={(e) => setSlPercent(Number(e.target.value))}
                        className="w-full accent-rose-500 bg-zinc-800 h-1 rounded cursor-pointer"
                      />

                      <div className="flex justify-between text-[10px] text-zinc-400">
                        <span>Take Profit (TP)</span>
                        <span className="font-mono text-zinc-200">{tpPercent}%</span>
                      </div>
                      <input
                        id="tp-percent-ranger"
                        type="range"
                        min="5"
                        max="60"
                        value={tpPercent}
                        onChange={(e) => setTpPercent(Number(e.target.value))}
                        className="w-full accent-emerald-500 bg-zinc-800 h-1 rounded cursor-pointer"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Real-time Scalper Active Positions Panel */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-zinc-400 font-bold uppercase tracking-wide flex items-center gap-1">
                    <ShoppingBag className="h-3 w-3 text-emerald-400" /> Active Scalps ({positions.length})
                  </span>
                  {positions.length > 0 && (
                    <button
                      id="close-all-trigger"
                      onClick={triggerCloseAll}
                      className="bg-rose-500/10 hover:bg-rose-500 text-rose-300 hover:text-white px-2 py-0.5 rounded border border-rose-500/20 text-[9px] font-bold"
                    >
                      EMERGENCY CLOSE ALL
                    </button>
                  )}
                </div>

                {positions.length === 0 ? (
                  <div className="bg-zinc-900/40 border border-zinc-800/80 border-dashed rounded-xl p-4 text-center text-zinc-500 text-xs">
                    No open trades in play. Tap Buy buttons or Option Chain strikes to deploy options scalping capital safely.
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-[160px] overflow-y-auto">
                    {positions.map((pos) => {
                      const valuePercentDiff = ((pos.currentPrice - pos.entryPrice) / pos.entryPrice) * 100;
                      return (
                        <div
                          id={`position-${pos.id}`}
                          key={pos.id}
                          className={`p-2.5 rounded-lg border ${
                            pos.pnl >= 0
                              ? "bg-emerald-950/20 border-emerald-500/20"
                              : "bg-rose-950/15 border-rose-500/20"
                          } text-xs flex flex-col`}
                        >
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-bold flex items-center gap-1.5 text-white">
                              {pos.type === "CE"
                                ? <span className="bg-emerald-500 text-black px-1 rounded text-[9px] font-black">CE</span>
                                : <span className="bg-rose-500 text-white px-1 rounded text-[9px] font-black">PE</span>
                              }
                              {pos.strike} Strike
                            </span>
                            <span className={`font-mono font-bold ${pos.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {pos.pnl >= 0 ? "+" : ""}₹{pos.pnl.toFixed(2)}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-y-1 gap-x-2 text-[10px] text-zinc-400 font-mono">
                            <div>Qty: <span className="text-zinc-200">{pos.quantity}</span></div>
                            <div>Pnd. %: <span className={pos.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}>{valuePercentDiff.toFixed(1)}%</span></div>
                            <div>Entry: <span className="text-zinc-200">₹{pos.entryPrice}</span></div>
                            <div>LTP: <span className="text-zinc-200">₹{pos.currentPrice}</span></div>
                          </div>

                          {/* Stoploss target markers indicator */}
                          <div className="flex gap-2 mt-1.5 pt-1.5 border-t border-zinc-800/60 text-[9px] text-zinc-500 font-mono">
                            {pos.stopLoss && <span className="mr-auto">SL: ₹{pos.stopLoss}</span>}
                            {pos.takeProfit && <span className="ml-auto">TP: ₹{pos.takeProfit}</span>}
                          </div>

                          <button
                            id={`close-scalp-${pos.id}`}
                            onClick={() => triggerMarketExit(pos.id)}
                            className="mt-2 bg-[#121319] hover:bg-zinc-800 text-zinc-300 py-1 rounded border border-zinc-800 font-bold text-[10px]"
                          >
                            Close Scalp Trade
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Collapsible Session Trade Log / History Panel */}
              <div className="border-t border-zinc-900 pt-3 mt-3 space-y-2">
                <button
                  id="trade-log-collapse-toggle"
                  onClick={() => setIsTradeLogOpen((o) => !o)}
                  className="w-full flex items-center justify-between text-[10px] text-zinc-400 font-bold uppercase tracking-wide hover:text-zinc-200 transition"
                >
                  <span className="flex items-center gap-1.5 font-sans">
                    <FileText className="h-3 w-3 text-amber-400" />
                    Session Trade Logs ({tradeHistory.length})
                  </span>
                  {isTradeLogOpen ? (
                    <ChevronUp className="h-3.5 w-3.5 text-zinc-500" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
                  )}
                </button>

                {isTradeLogOpen && (
                  <div className="bg-zinc-950/40 border border-zinc-900 rounded-xl p-2 max-h-[160px] overflow-y-auto space-y-1.5 scrollbar-thin">
                    {tradeHistory.length === 0 ? (
                      <div className="text-[10px] text-zinc-500 text-center py-2.5 leading-relaxed">
                        No transactions registered yet. Active or exited trades will compile here in real-time.
                      </div>
                    ) : (
                      tradeHistory.map((trade) => {
                        const isWin = trade.status === "CLOSED" && trade.pnl > 0;
                        const isLoss = trade.status === "CLOSED" && trade.pnl < 0;
                        return (
                          <div
                            id={`history-item-${trade.id}`}
                            key={trade.id}
                            className={`p-2 rounded border text-[10px] flex flex-col gap-1 ${
                              trade.status === "ACTIVE"
                                ? "bg-emerald-950/5 border-emerald-500/10"
                                : "bg-zinc-900/40 border-zinc-850"
                            }`}
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-bold font-sans flex items-center gap-1">
                                {trade.type === "CE" ? (
                                  <span className="bg-emerald-500 text-black px-1 rounded text-[8px] font-black leading-tight">CE</span>
                                ) : (
                                  <span className="bg-rose-500 text-white px-1 rounded text-[8px] font-black leading-tight">PE</span>
                                )}
                                {trade.strike}
                              </span>
                              <span className={`font-mono font-bold ${
                                trade.status === "ACTIVE"
                                  ? "text-zinc-400"
                                  : isWin
                                  ? "text-emerald-400"
                                  : isLoss
                                  ? "text-rose-400"
                                  : "text-zinc-500"
                              }`}>
                                {trade.status === "ACTIVE" ? (
                                  <span className="text-[8px] px-1 py-0.2 rounded bg-emerald-500/10 text-emerald-400 animate-pulse font-bold">LIVE</span>
                                ) : (
                                  `₹${trade.pnl > 0 ? "+" : ""}${trade.pnl.toFixed(1)}`
                                ) || "₹0.0"}
                              </span>
                            </div>

                            <div className="grid grid-cols-2 gap-y-0.5 gap-x-1.5 text-[9px] text-zinc-500 font-mono">
                              <div>Qty: <span className="text-zinc-300">{trade.quantity}</span></div>
                              <div>Side: <span className="text-zinc-300 font-bold">{trade.side || "BUY"}</span></div>
                              <div className="col-span-2 border-t border-zinc-900/60 my-0.5" />
                              <div className="col-span-2 flex items-center justify-between text-[8px]">
                                <span>Entry: <b className="text-zinc-300">₹{trade.entryPrice}</b></span>
                                {trade.entrySpot && <span>Spot: <b className="text-zinc-400">{trade.entrySpot.toFixed(1)}</b></span>}
                              </div>
                              {trade.status === "CLOSED" && (
                                <div className="col-span-2 flex items-center justify-between text-[8px] bg-black/25 px-1 py-0.5 rounded mt-0.5">
                                  <span>Exit: <b className="text-zinc-300">₹{trade.exitPrice?.toFixed(1)}</b></span>
                                  {trade.exitSpot && <span>Spot: <b className="text-zinc-400">{trade.exitSpot.toFixed(1)}</b></span>}
                                </div>
                              )}
                            </div>

                            {trade.status === "CLOSED" && trade.exitReason && (
                              <div className="text-[8px] text-zinc-400 bg-zinc-950/60 px-1 py-0.5 rounded font-mono mt-0.5 capitalize flex justify-between items-center">
                                <span>Exit Code:</span>
                                <span className={isWin ? "text-emerald-400" : isLoss ? "text-rose-400" : "text-zinc-300"}>
                                  {trade.exitReason}
                                </span>
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Quick account details metadata footer */}
            <div className="bg-[#12141c] p-2.5 rounded-lg border border-zinc-800/85 text-[10px] space-y-1 mt-auto">
              <div className="flex justify-between">
                <span className="text-zinc-500">Margin In Play:</span>
                <span className="font-mono text-zinc-300 font-semibold">₹{activeMarginInPlay.toLocaleString("en-IN")}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Total Unr PNL:</span>
                <span className={`font-mono font-bold ${totalPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  ₹{totalPnL.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between border-t border-zinc-800 pt-1 mt-1 font-bold text-zinc-300">
                <span>Free Balance:</span>
                <span>₹{(accountBalance).toLocaleString("en-IN", { maximumFractionDigits: 1 })}</span>
              </div>
            </div>
          </section>

          {/* COLUMN 2: CHARTS PANEL (6 cols) */}
          <section id="charts-panel" className="lg:col-span-6 flex flex-col gap-1.5">
            {/* DUCKDB HISTORICAL REPLAY CONTROL BAR DECK */}
            {dataSource === "replay" && (
              <div id="duckdb-replay-deck" className="bg-[#0b0c10] border border-amber-500/25 rounded-xl p-3 flex flex-col gap-2.5 shadow-lg shadow-amber-500/5 transition animate-fade-in text-xs">
                {/* Dual replay/backtest selector bar */}
                <div className="flex items-center justify-between border-b border-zinc-850 pb-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-amber-500" />
                    <span className="font-extrabold text-amber-400 font-mono tracking-wider text-[10px] uppercase">GEX REPLAY ARCHIVES</span>
                  </div>
                  <div className="flex items-center gap-1.5 bg-zinc-950/80 p-0.5 border border-zinc-900 rounded-lg">
                    <button
                      id="replay-mode-visual-btn"
                      onClick={() => setReplayMode("visual")}
                      className={`px-2.5 py-1 rounded text-[10px] font-extrabold uppercase transition-all duration-150 cursor-pointer ${
                        replayMode === "visual" ? "bg-amber-500 text-black shadow font-bold" : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      Normal Replay
                    </button>
                    <button
                      id="replay-mode-backtest-btn"
                      onClick={() => setReplayMode("backtest")}
                      className={`px-2.5 py-1 rounded text-[10px] font-extrabold uppercase transition-all duration-150 cursor-pointer ${
                        replayMode === "backtest" ? "bg-amber-500 text-black shadow font-bold" : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      Backtest / No Screen
                    </button>
                  </div>
                </div>

                {replayMode === "visual" ? (
                  <>
                    {/* Deck Line 1: DB file, playing switch, speed index, and bot active flag */}
                    <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                        <span className="font-bold text-zinc-400">Database:</span>

                        {/* Database file options dropdown selector */}
                        <select
                          id="replay-file-select"
                          value={selectedReplayFile}
                          onChange={(e) => setSelectedReplayFile(e.target.value)}
                          className="bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-100 px-2 py-1 rounded text-xs focus:ring-1 focus:ring-amber-500 font-bold focus:outline-none cursor-pointer"
                        >
                          {replayFiles.length > 0 ? (
                            replayFiles.map((file) => (
                              <option key={file.id} value={file.id}>
                                {file.name}
                              </option>
                            ))
                          ) : (
                            <>
                              <option value="20260421.duckdb">Expiry 21-Apr-2026</option>
                              <option value="20260413.duckdb">Expiry 13-Apr-2026</option>
                              <option value="20260407.duckdb">Expiry 07-Apr-2026</option>
                            </>
                          )}
                        </select>

                        {/* Trading Date Dropdown Selector */}
                        {replayDates.length > 0 && (
                          <div className="flex items-center gap-1.5 ml-1">
                            <span className="text-[9px] text-zinc-550 font-extrabold font-mono tracking-tight">DAY:</span>
                            <select
                              id="replay-date-select"
                              value={selectedReplayDate}
                              onChange={(e) => setSelectedReplayDate(e.target.value)}
                              className="bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-amber-400 px-2 py-1 rounded text-xs font-extrabold focus:ring-1 focus:ring-amber-500 focus:outline-none cursor-pointer"
                            >
                              {replayDates.map((d) => {
                                const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                                const parts = d.split("-");
                                let displayStr = d;
                                if (parts.length === 3) {
                                  const day = parts[2];
                                  const monthIdx = parseInt(parts[1], 10) - 1;
                                  const year = parts[0];
                                  if (monthIdx >= 0 && monthIdx < 12) {
                                    displayStr = `${day}-${months[monthIdx]}-${year}`;
                                  }
                                }
                                return (
                                  <option key={d} value={d}>
                                    {displayStr} {d === replayDates[replayDates.length - 1] ? "(Expiry)" : ""}
                                  </option>
                                );
                              })}
                              <option value="all">All Combined</option>
                            </select>
                          </div>
                        )}

                        {replayLoading && (
                          <span className="text-[10px] text-zinc-400 font-mono animate-pulse">Retexturing timeline...</span>
                        )}
                      </div>

                      {/* Operational Walk buttons */}
                      <div className="flex items-center gap-2">
                        <button
                          id="replay-play-pause"
                          onClick={() => setIsPlaying(!isPlaying)}
                          className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-black transition duration-150 cursor-pointer ${
                            isPlaying
                              ? "bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/40"
                              : "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/40"
                          }`}
                        >
                          {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                          {isPlaying ? "PAUSE walk" : "WALK TICK"}
                        </button>

                        {/* Speed modifiers */}
                        <div className="flex items-center bg-zinc-900 border border-zinc-850 rounded px-1.5 py-0.5 gap-1">
                          <span className="text-[9px] text-zinc-500 font-mono uppercase font-black">SPEED</span>
                          <select
                            id="replay-speed-select"
                            value={config.speedMultiplier}
                            onChange={(e) => setConfig((prev) => ({ ...prev, speedMultiplier: Number(e.target.value) }))}
                            className="bg-transparent text-amber-400 font-mono font-bold text-[10px] border-none focus:ring-0 p-0 cursor-pointer focus:outline-none"
                          >
                            <option value="1">1x</option>
                            <option value="2">2x Fast</option>
                            <option value="5">5x Scalper</option>
                            <option value="10">10x Extreme</option>
                          </select>
                        </div>

                        <div className="h-4 w-[1px] bg-zinc-800" />

                        {/* Auto trader execution BOT */}
                        <button
                          id="replay-auto-trader-toggle"
                          onClick={() => {
                            setIsAutoTrader(!isAutoTrader);
                            setLastOrderAlert({
                              type: "success",
                              msg: `Auto-Scalper trading bot ${!isAutoTrader ? "ACTIVATED" : "DEACTIVATED"}. It will automatically execute trades on confluence signals.`
                            });
                          }}
                          className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-extrabold uppercase transition border tracking-wider cursor-pointer ${
                            isAutoTrader
                              ? "bg-emerald-950/40 text-emerald-400 border-emerald-500 animate-pulse shadow-lg shadow-emerald-500/5"
                              : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                          }`}
                        >
                          <Cpu className="h-3.5 w-3.5" />
                          AUTO SCALPER BOT: {isAutoTrader ? "ONLINE" : "OFFLINE"}
                        </button>
                      </div>
                    </div>

                    {/* Deck Line 2: Scrubber timeline range slider */}
                    <div className="flex items-center gap-3 bg-zinc-950 rounded-xl p-2 border border-zinc-900">
                      <div className="text-[10px] font-mono text-amber-400 font-extrabold w-18 text-center select-none bg-zinc-900 border border-zinc-850 px-1 py-0.5 rounded">
                        {replayTimestamps[replayCurrentIndex]?.timestamp.split(" ")[1] || "09:15:00"}
                      </div>

                      <input
                        id="replay-scrubber-slider"
                        type="range"
                        min="0"
                        max={Math.max(0, replayTimestamps.length - 1)}
                        value={replayCurrentIndex}
                        onChange={(e) => {
                          setReplayCurrentIndex(Number(e.target.value));
                        }}
                        className="flex-1 accent-amber-500 bg-zinc-850 h-1.5 rounded-lg cursor-pointer"
                      />

                      <div className="text-[10px] font-mono text-zinc-400 w-28 text-right select-none">
                         Tick Index {replayCurrentIndex + 1} / {replayTimestamps.length}
                      </div>
                    </div>

                    {/* Deck Line 3: Bot statistics & logs */}
                    {isAutoTrader && (
                      <div className="bg-[#0e2c1c]/10 rounded-lg p-2.5 border border-emerald-500/20 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono">
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-400 font-black uppercase text-[9px] bg-emerald-950/60 px-1.5 py-0.5 rounded">STATISTICS PROFILE:</span>
                          <span className="text-zinc-300">Net Auto Executions logs in real-time</span>
                        </div>

                        {(() => {
                          const closedPositions = positions.filter((p) => p.exitReason !== undefined);
                          const winningCount = closedPositions.filter((p) => p.pnl > 0).length;
                          const winRate = closedPositions.length > 0 ? Math.round((winningCount / closedPositions.length) * 100) : 0;
                          const netClosedPnL = closedPositions.reduce((acc, p) => acc + p.pnl, 0);
                          return (
                            <div className="flex gap-4 select-none text-[10px]">
                              <span className="text-zinc-400">TRADES: <strong className="text-white">{closedPositions.length}</strong></span>
                              <span className="text-zinc-400">WIN RATE: <strong className={winRate >= 50 ? "text-emerald-400 animate-pulse" : "text-amber-400"}>{winRate}%</strong></span>
                              <span className="text-zinc-400">NET PNL: <strong className={netClosedPnL >= 0 ? "text-emerald-400 font-black animate-pulse" : "text-rose-400 font-black"}>₹{netClosedPnL.toFixed(1)}</strong></span>
                            </div>
                          );
                        })()}
                      </div>
                    )}
                  </>
                ) : (
                  /* Backtest control screenless module dashboard */
                  <div className="space-y-3 py-1 animate-fade-in text-zinc-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">

                      {/* Left: Settings Selection */}
                      <div className="space-y-2">
                        <div className="flex flex-col gap-1">
                          <label className="text-[10px] font-black text-zinc-500 font-mono tracking-wider uppercase">1. Replay Source Archive</label>
                          <select
                            id="backtest-file-select"
                            value={selectedReplayFile}
                            onChange={(e) => setSelectedReplayFile(e.target.value)}
                            className="bg-zinc-900 border border-zinc-800 text-white p-1.5 rounded text-xs focus:ring-1 focus:ring-amber-500 font-bold cursor-pointer w-full focus:outline-none"
                          >
                            {replayFiles.map((file) => (
                              <option key={file.id} value={file.id}>
                                {file.name}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="flex flex-col gap-1">
                          <label className="text-[10px] font-black text-zinc-500 font-mono tracking-wider uppercase">2. Target Evaluation Date</label>
                          <select
                            id="backtest-date-select"
                            value={selectedReplayDate}
                            onChange={(e) => setSelectedReplayDate(e.target.value)}
                            className="bg-zinc-900 border border-[#27272a] text-amber-400 p-1.5 rounded text-xs font-black cursor-pointer w-full focus:outline-none"
                          >
                            {replayDates.map((d) => {
                              const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                              const parts = d.split("-");
                              let displayStr = d;
                              if (parts.length === 3) {
                                const day = parts[2];
                                const monthIdx = parseInt(parts[1], 10) - 1;
                                const year = parts[0];
                                if (monthIdx >= 0 && monthIdx < 12) {
                                  displayStr = `${day}-${months[monthIdx]}-${year}`;
                                }
                              }
                              return (
                                <option key={d} value={d}>
                                  {displayStr} {d === replayDates[replayDates.length - 1] ? "(Expiry)" : ""}
                                </option>
                              );
                            })}
                            <option value="all">All Combined</option>
                          </select>
                        </div>
                      </div>

                      {/* Right: Risk Configuration Deck */}
                      <div className="space-y-2 text-xs">
                        <label className="text-[10px] font-black text-zinc-500 font-mono tracking-wider uppercase">3. Risk Management Deck</label>
                        <div className="grid grid-cols-2 gap-2 bg-zinc-900/60 p-2.5 rounded-lg border border-zinc-850">
                          <div>
                            <span className="text-[10px] text-zinc-400 font-bold block mb-1">Stop Loss</span>
                            <div className="flex items-center gap-1">
                              <button onClick={() => setSlPercent(Math.max(2, slPercent - 2))} className="px-1.5 py-0.5 bg-zinc-850 hover:bg-zinc-800 rounded font-bold border border-zinc-750">-</button>
                              <span className="text-amber-400 font-mono font-bold text-xs">{slPercent}%</span>
                              <button onClick={() => setSlPercent(Math.min(50, slPercent + 2))} className="px-1.5 py-0.5 bg-zinc-850 hover:bg-zinc-800 rounded font-bold border border-zinc-750">+</button>
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] text-zinc-400 font-bold block mb-1">Take Profit</span>
                            <div className="flex items-center gap-1">
                              <button onClick={() => setTpPercent(Math.max(5, tpPercent - 5))} className="px-1.5 py-0.5 bg-zinc-850 hover:bg-zinc-800 rounded font-bold border border-zinc-750">-</button>
                              <span className="text-emerald-400 font-mono font-bold text-xs">{tpPercent}%</span>
                              <button onClick={() => setTpPercent(Math.min(150, tpPercent + 5))} className="px-1.5 py-0.5 bg-zinc-850 hover:bg-zinc-800 rounded font-bold border border-zinc-750">+</button>
                            </div>
                          </div>
                          <div className="col-span-2 pt-1 border-t border-zinc-800 flex items-center justify-between">
                            <span className="text-[10px] text-zinc-400 font-semibold font-mono uppercase tracking-tight text-[9px]">Lot Multiplier:</span>
                            <input
                              type="number"
                              min="50"
                              max="1000"
                              step="50"
                              value={tradeQuantity}
                              onChange={(e) => setTradeQuantity(Number(e.target.value))}
                              className="bg-zinc-950 border border-zinc-800 text-zinc-200 px-1.5 py-0.5 rounded w-16 text-center font-mono focus:outline-none"
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Auto-Scalping Bot strategy engagement info */}
                    <div className="bg-emerald-950/15 border border-emerald-500/20 rounded-lg p-2.5 flex items-start gap-2.5">
                      <Cpu className="h-4.5 w-4.5 text-emerald-400 flex-shrink-0 mt-0.5 animate-pulse" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-black uppercase text-emerald-400 font-mono tracking-wide">STRATEGY BOT ENGAGEMENT</span>
                          <span className="text-[9px] bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 px-1 py-0.2 rounded font-extrabold">AUTO ENFORCED</span>
                        </div>
                        <p className="text-[10.5px] text-zinc-400 leading-normal mt-0.5">
                          Screenless backtest queries of the high-conviction scalper. It scans contract tickers for trade signals conforming to intra-day timing constraints (09:19 to 15:15) and hard liquidates outstanding scalps at 15:25.
                        </p>
                      </div>
                    </div>

                    {/* Progress tracking container */}
                    {isBacktesting ? (
                      <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-900 space-y-2">
                        <div className="flex justify-between items-center text-[11px]">
                          <span className="text-amber-400 font-black flex items-center gap-1.5 font-mono">
                            <RefreshCw className="h-3 w-3 animate-spin" /> RUNNING ALGO SIMULATIONS...
                          </span>
                          <span className="text-zinc-400 font-mono font-bold">
                            {backtestProgress ? `${backtestProgress.current} / ${backtestProgress.total} ticks (${Math.round((backtestProgress.current / backtestProgress.total) * 100)}%)` : "Initializing data streams..."}
                          </span>
                        </div>
                        <div className="w-full bg-zinc-850 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-amber-500 to-emerald-500 h-full transition-all duration-150 animate-pulse"
                            style={{
                              width: backtestProgress ? `${Math.min(100, Math.round((backtestProgress.current / backtestProgress.total) * 100))}%` : "5%",
                            }}
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          id="btn-trigger-backtest"
                          onClick={() => {
                            setIsAutoTrader(true); // Ensure auto-trader mode is logically active for calculations
                            runReplayBacktest();
                          }}
                          className="flex-1 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold uppercase py-2.5 px-4 rounded-xl text-center shadow-lg hover:shadow-xl transition-all duration-150 tracking-wider cursor-pointer font-sans"
                        >
                          RUN HISTORICAL ALGO BACKTEST
                        </button>
                      </div>
                    )}

                    {/* Highlighted result of last test run */}
                    {backtestResult && !isBacktesting && (
                      <div className="bg-[#12141a] border border-[#2b2b35] rounded-xl p-3 flex flex-col gap-2 shadow-inner">
                        <div className="flex items-center justify-between border-b border-zinc-850 pb-1.5 mb-1 text-[10px] font-black text-zinc-400 font-mono tracking-wider uppercase">
                          <span>LAST RUN OUTCOMES</span>
                          <span className="text-emerald-400 font-semibold font-mono">SUCCESS</span>
                        </div>

                        <div className="grid grid-cols-4 gap-2 text-center select-none font-sans">
                          <div className="bg-zinc-950/40 p-1.5 rounded-lg border border-zinc-900/60 animate-fade-in">
                            <span className="text-[9px] text-zinc-500 font-bold block mb-0.5">NET PROFIT</span>
                            <span className={`text-xs font-black font-mono ${backtestResult.profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              ₹{backtestResult.profit.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                            </span>
                          </div>

                          <div className="bg-zinc-950/40 p-1.5 rounded-lg border border-zinc-900/60 animate-fade-in">
                            <span className="text-[9px] text-zinc-500 font-bold block mb-0.5">TOTAL TRADES</span>
                            <span className="text-xs font-black font-mono text-zinc-100">{backtestResult.totalTrades}</span>
                          </div>

                          <div className="bg-zinc-950/40 p-1.5 rounded-lg border border-zinc-900/60 animate-fade-in">
                            <span className="text-[9px] text-zinc-500 font-bold block mb-0.5">WIN RATE</span>
                            <span className="text-xs font-black font-mono text-emerald-400">{backtestResult.winRate.toFixed(1)}%</span>
                          </div>

                          <div className="bg-zinc-950/40 p-1.5 rounded-lg border border-zinc-900/60 animate-fade-in">
                            <span className="text-[9px] text-zinc-500 font-bold block mb-0.5">COMPLIANCE</span>
                            <span className="text-xs font-black font-mono text-zinc-200">{backtestResult.compliance}%</span>
                          </div>
                        </div>

                        <button
                          onClick={() => setActiveTab("pnl_analysis")}
                          className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-amber-400 font-black uppercase py-1.5 rounded-md text-center mt-1 transition cursor-pointer"
                        >
                          Navigate to Performance Sheet
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Custom Multi-monitor Zoom controls */}
            <div className="bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-2.5 flex items-center justify-between text-xs gap-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-emerald-400" />
                <span className="font-bold text-zinc-200">Interactive Low-Latency Charts</span>
              </div>

              {/* Layout type modifiers */}
              <div className="flex bg-zinc-950 rounded p-0.5 border border-zinc-800">
                <button
                  id="view-side-by-side"
                  onClick={() => setConfig((prev) => ({ ...prev, layout: "side-by-side" }))}
                  className={`px-2 py-0.5 rounded text-[10px] ${
                    config.layout === "side-by-side" ? "bg-zinc-850 text-white font-bold" : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  Dual Split View
                </button>
                <button
                  id="view-single"
                  onClick={() => setConfig((prev) => ({ ...prev, layout: "single" }))}
                  className={`px-2 py-0.5 rounded text-[10px] ${
                    config.layout === "single" ? "bg-zinc-850 text-white font-bold" : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  Spot Full Canvas
                </button>
              </div>

              {/* Timeframe selector locks */}
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-zinc-500 font-mono">LOCK:</span>
                <div className="flex bg-zinc-950 p-0.5 rounded border border-zinc-850">
                  {["1m", "5m", "15m"].map((tf) => (
                    <button
                      id={`lock-tf-${tf}`}
                      key={tf}
                      onClick={() => setConfig((prev) => ({ ...prev, timeframeLock: tf as any }))}
                      className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                        config.timeframeLock === tf ? "bg-zinc-800 text-emerald-400 font-bold" : "text-zinc-500 hover:text-zinc-300"
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>

              {/* Volume Weighted Candlesticks Toggle */}
              <button
                id="toggle-vw-candles-btn"
                onClick={() => setIsVolWeighted((v) => !v)}
                className={`px-2 py-0.5 rounded border text-[10px] font-mono transition ${
                  isVolWeighted
                    ? "bg-amber-500/15 text-amber-400 border-amber-500/20 font-bold"
                    : "bg-zinc-900 border-zinc-805 text-zinc-400 hover:text-zinc-200"
                }`}
                title="Scale candle width proportional to relative trading volume"
              >
                ⚖️ VOL WEIGHTED: {isVolWeighted ? "ON" : "OFF"}
              </button>

              {/* Zoom buttons */}
              <div className="flex items-center gap-1 font-mono">
                <span className="text-[10px] text-zinc-500 mr-1">ZOOM ({viewportCandles} bars)</span>
                <button
                  id="zoom-out-btn"
                  onClick={() => handleZoom(4)}
                  className="bg-zinc-900 border border-zinc-800 hover:bg-zinc-805 text-zinc-300 px-2 py-0.5 rounded text-[10px]"
                >
                  -
                </button>
                <button
                  id="zoom-in-btn"
                  onClick={() => handleZoom(-4)}
                  className="bg-zinc-900 border border-zinc-800 hover:bg-zinc-805 text-zinc-300 px-2 py-0.5 rounded text-[10px]"
                >
                  +
                </button>
              </div>
            </div>

            {/* CHART 1: SPOT INDEX CHART WITH OPTION OVERLAY */}
            <div
              id="spot-spot-chart"
              className="bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-3 flex-1 flex flex-col justify-between overflow-hidden relative"
              onMouseLeave={() => setHoverIndex(null)}
            >
              <div className="flex justify-between items-center border-b border-zinc-800/80 pb-2 mb-2 z-10">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white uppercase tracking-wide">
                    {instrument} SPOT UNDERLYING INDEX
                  </span>
                  <span className="bg-zinc-850 border border-zinc-800 text-zinc-400 text-[10px] px-1.5 py-0.2 rounded">
                    Zone Analysis On
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-400">
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-orange-400"></span> VWAP
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-400"></span> 9 EMA
                  </span>
                </div>
              </div>

              {/* Candle stats hover window */}
              {hoverIndex !== null && spotCandles[hoverIndex] && (
                <div id="candle-hover-overlay" className="absolute top-12 left-4 z-20 bg-black/90 border border-zinc-800 p-2 rounded-lg text-[10px] font-mono space-y-0.5 pointer-events-none shadow-2xl">
                  <div>Time: {new Date(spotCandles[hoverIndex].time * 1000).toLocaleTimeString()}</div>
                  <div className="flex gap-2">
                    <span>O: <span className="text-zinc-100">{spotCandles[hoverIndex].open.toFixed(1)}</span></span>
                    <span>H: <span className="text-emerald-400">{spotCandles[hoverIndex].high.toFixed(1)}</span></span>
                    <span>L: <span className="text-rose-400">{spotCandles[hoverIndex].low.toFixed(1)}</span></span>
                    <span>C: <span className="text-zinc-100">{spotCandles[hoverIndex].close.toFixed(1)}</span></span>
                  </div>
                  {spotCandles[hoverIndex].vwap && <div>VWAP: <span className="text-amber-400">{spotCandles[hoverIndex].vwap}</span></div>}
                  {spotCandles[hoverIndex].ema && <div>EMA: <span className="text-sky-400">{spotCandles[hoverIndex].ema?.toFixed(1)}</span></div>}
                </div>
              )}

              {/* HIGH PERFORMANCE CUSTOM SVG SPOT CHART */}
              <div className="flex-1 min-h-[160px] relative">
                {displaySpotCandles.length === 0 ? (
                  <div className="absolute inset-0 flex items-center justify-center text-zinc-500 text-xs">
                    Synthesizing low-latency charts...
                  </div>
                ) : (
                  <svg className="w-full h-full" style={{ overflow: "visible" }}>
                    {(() => {
                      // Get min/max coordinates of visible candlestick series
                      const paddingPct = 0.05;
                      const prices = displaySpotCandles.flatMap((c) => [c.high, c.low]);
                      const maxPrice = Math.max(...prices);
                      const minPrice = Math.min(...prices);
                      const delta = maxPrice - minPrice || 10;
                      const yMax = maxPrice + delta * paddingPct;
                      const yMin = minPrice - delta * paddingPct;

                      const svgWidth = 520; // safe scale
                      const svgHeight = 240;

                      const avgVolume = displaySpotCandles.reduce((acc, curr) => acc + (curr.volume || 0), 0) / displaySpotCandles.length || 1;

                      // Map prices to coordinate space helper
                      const getX = (idx: number) => {
                        return (idx / (displaySpotCandles.length - 1)) * 88 + "%"; // Keep trailing padding
                      };
                      const getY = (price: number) => {
                        return (1 - (price - yMin) / (yMax - yMin)) * 100 + "%";
                      };

                      return (
                        <>
                          {/* AUTOMATIC MARKET STRUCTURE / LIQUIDITY ZONES BACKGROUND */}
                          {mStructures.orderBlocks.map((ob, kIdx) => {
                            const yTop = getY(Math.max(ob.priceStart, ob.priceEnd));
                            const yBottom = getY(Math.min(ob.priceStart, ob.priceEnd));
                            const isBull = ob.type === "bullish";
                            return (
                              <g key={`ob-${kIdx}`} className="opacity-15">
                                <rect
                                  x="0%"
                                  width="90%"
                                  y={yTop}
                                  height={`calc(${yBottom} - ${yTop})`}
                                  fill={isBull ? "#10b981" : "#ef4444"}
                                />
                                <text
                                  x="4"
                                  y={`calc(${yTop} + 12px)`}
                                  fill={isBull ? "#34d399" : "#f87171"}
                                  fontSize="9"
                                  fontWeight="bold"
                                  fontFamily="monospace"
                                >
                                  {isBull ? "BULLISH ORDER BLOCK / LIQUIDITY ZONE" : "BEARISH REJECTION BLOCK"}
                                </text>
                              </g>
                            );
                          })}

                          {mStructures.fairValueGaps.map((fvg, fIdx) => {
                            if (fvg.isFilled) return null;
                            const yTop = getY(fvg.top);
                            const yBottom = getY(fvg.bottom);
                            return (
                              <g key={`fvg-${fIdx}`} className="opacity-10">
                                <rect
                                  x="10%"
                                  width="75%"
                                  y={yTop}
                                  height={`calc(${yBottom} - ${yTop})`}
                                  fill="#ec4899"
                                  stroke="#ec4899"
                                  strokeDasharray="2,2"
                                />
                                <text
                                  x="9%"
                                  y={`calc(${yTop} + 10px)`}
                                  fill="#f472b6"
                                  fontSize="8"
                                  fontFamily="monospace"
                                >
                                  FAIR VALUE GAP (FVG)
                                </text>
                              </g>
                            );
                          })}

                          {/* SPOT HORIZONTAL SEMI-TRANSPARENT OI UNDERLAY BAR MATRIX */}
                          {strikes.map((st, sK) => {
                            const rowY = getY(st.strike);
                            const callPct = Math.min(100, (st.callOI / 200000) * 40);
                            const putPct = Math.min(100, (st.putOI / 200000) * 40);
                            return (
                              <g key={`oi-row-${sK}`} className="opacity-35 hover:opacity-85 pointer-events-none">
                                {/* Strike coordinate label line */}
                                <line x1="0%" y1={rowY} x2="90%" y2={rowY} stroke="#3f3f46" strokeWidth="0.5" strokeDasharray="1,4" />
                                <text x="91%" y={`calc(${rowY} + 4px)`} fill="#a1a1aa" fontSize="8" fontFamily="monospace" textAnchor="start">
                                  {st.strike}
                                </text>

                                {/* Call write bar (red, aligned to right axis projection) */}
                                <rect
                                  x={`calc(90% - ${callPct}px)`}
                                  y={`calc(${rowY} - 3px)`}
                                  width={`${callPct}px`}
                                  height="6"
                                  fill="#ef4444"
                                  rx="1"
                                />

                                {/* Put write bar (green, aligned to right axis projection) */}
                                <rect
                                  x="90%"
                                  y={`calc(${rowY} - 3px)`}
                                  width={`${putPct}px`}
                                  height="6"
                                  fill="#10b981"
                                  rx="1"
                                />
                              </g>
                            );
                          })}

                          {/* NET GAMMA EXPOSURE (GEX) PROFILE OVERLAY CHART */}
                          {/* Vertical Zero-Axis for GEX Profile at x = 12% */}
                          <line x1="12%" y1="0%" x2="12%" y2="100%" stroke="#3f3f46" strokeWidth="0.8" strokeDasharray="2,3" opacity="0.6" />
                          <text x="12%" y="10" fill="#a1a1aa" fontSize="7" fontFamily="monospace" textAnchor="middle" opacity="0.7">
                            GEX ZERO AXIS
                          </text>

                          {gexProfile.map((gp, gpK) => {
                            const rowY = getY(gp.strike);
                            const maxGexVal = Math.max(...gexProfile.map((g) => Math.abs(g.netGEX))) || 1;
                            const barWidth = Math.min(60, (Math.abs(gp.netGEX) / maxGexVal) * 55);

                            const isPositive = gp.netGEX >= 0;
                            const widthPct = (barWidth / 5); // max ~11% width
                            const xVal = isPositive ? "12%" : `calc(12% - ${widthPct}%)`;

                            return (
                              <g key={`gex-row-${gpK}`} className="opacity-45 hover:opacity-90 pointer-events-none">
                                {/* Strike reference line */}
                                <line x1="2%" y1={rowY} x2="22%" y2={rowY} stroke="#27272a" strokeWidth="0.5" />

                                {/* GEX Profile bar */}
                                <rect
                                  x={xVal}
                                  y={`calc(${rowY} - 3px)`}
                                  width={`${widthPct}%`}
                                  height="6"
                                  fill={isPositive ? "#059669" : "#e11d48"} // Emerald-600 vs Rose-600
                                  rx="1"
                                  className="transition-all duration-300"
                                />

                                {/* Micro GEX value label */}
                                {isPositive ? (
                                  <text x={`calc(12% + ${widthPct}% + 3px)`} y={`calc(${rowY} + 2px)`} fill="#34d399" fontSize="7" fontFamily="monospace">
                                    +{Math.round(gp.netGEX / 1000)}k
                                  </text>
                                ) : (
                                  <text x={`calc(12% - ${widthPct}% - 14px)`} y={`calc(${rowY} + 2px)`} fill="#f47171" fontSize="7" fontFamily="monospace">
                                    {Math.round(gp.netGEX / 1000)}k
                                  </text>
                                )}
                              </g>
                            );
                          })}

                          {/* VOLATILITY TRIGGER FLIP ZONE OVERLAY */}
                          {volatilityTrigger > 0 && (() => {
                            const triggerY = getY(volatilityTrigger);
                            const flipZoneDist = instrument === InstrumentType.NIFTY ? 10 : 25;
                            const yTopFlip = getY(volatilityTrigger + flipZoneDist);
                            const yBottomFlip = getY(volatilityTrigger - flipZoneDist);

                            return (
                              <g id="volatility-trigger-overlay">
                                {/* Shaded volatility zone range */}
                                <rect
                                  x="0%"
                                  width="90%"
                                  y={yTopFlip}
                                  height={`calc(${yBottomFlip} - ${yTopFlip})`}
                                  fill="#db2777"
                                  opacity="0.08"
                                  pointerEvents="none"
                                />

                                {/* Horizontal reference line */}
                                <line
                                  x1="0%"
                                  y1={triggerY}
                                  x2="90%"
                                  y2={triggerY}
                                  stroke="#ec4899" // Pink-500
                                  strokeWidth="1.5"
                                  strokeDasharray="4,2"
                                  className="animate-pulse"
                                />

                                {/* Volatility trigger label */}
                                <rect
                                  x="4%"
                                  y={`calc(${triggerY} - 8px)`}
                                  width="145"
                                  height="16"
                                  rx="3"
                                  fill="#db2777" // Pink-600
                                  opacity="0.9"
                                />
                                <text
                                  x="5%"
                                  y={`calc(${triggerY} + 3px)`}
                                  fill="#ffffff"
                                  fontSize="8"
                                  fontWeight="bold"
                                  fontFamily="monospace"
                                >
                                  VOL TRIGGER FLIP: {volatilityTrigger}
                                </text>
                              </g>
                            );
                          })()}

                          {/* Technical Indicators: Spot VWAP lines */}
                          <polyline
                            fill="none"
                            stroke="#f59e0b"
                            strokeWidth="1.2"
                            strokeDasharray="2,2"
                            points={displaySpotCandles
                              .map((c, idx) => c.vwap ? `${(idx / (displaySpotCandles.length - 1)) * 88}%,${getY(c.vwap)}` : "")
                              .filter(Boolean)
                              .join(" ")}
                          />

                          {/* Technical Indicators: Spot 9 EMA lines */}
                          <polyline
                            fill="none"
                            stroke="#06b6d4"
                            strokeWidth="1.5"
                            points={displaySpotCandles
                              .map((c, idx) => c.ema ? `${(idx / (displaySpotCandles.length - 1)) * 88}%,${getY(c.ema)}` : "")
                              .filter(Boolean)
                              .join(" ")}
                          />

                          {/* Candlestick visualization */}
                          {displaySpotCandles.map((c, idx) => {
                            const isGreen = c.close >= c.open;
                            const xVal = `${(idx / (displaySpotCandles.length - 1)) * 88}%`;
                            const wickTop = getY(c.high);
                            const wickBot = getY(c.low);
                            const bodyTop = getY(Math.max(c.open, c.close));
                            const bodyBot = getY(Math.min(c.open, c.close));

                            const relVol = avgVolume > 0 ? (c.volume || 0) / avgVolume : 1;
                            const candleWidth = isVolWeighted
                              ? Math.max(2.5, Math.min(22, 8 * relVol))
                              : 8;

                            return (
                              <g key={`spot-cand-${idx}`} onMouseEnter={() => setHoverIndex(idx)} className="cursor-crosshair">
                                {/* Wick queue */}
                                <line
                                  x1={xVal}
                                  y1={wickTop}
                                  x2={xVal}
                                  y2={wickBot}
                                  stroke={isGreen ? "#10b981" : "#f43f5e"}
                                  strokeWidth="1.5"
                                />
                                {/* Candle Body block */}
                                <rect
                                  x={`calc(${xVal} - ${candleWidth / 2}px)`}
                                  y={bodyTop}
                                  width={candleWidth}
                                  height={`calc(${bodyBot} - ${bodyTop} + 1px)`}
                                  fill={isGreen ? "#10b981" : "#f43f5e"}
                                  stroke={isGreen ? "#047857" : "#be123c"}
                                  strokeWidth="0.5"
                                  rx="1"
                                />

                                {/* Trade Entry/Exit Markers */}
                                {tradeHistory.map((trade, tIdx) => {
                                  const isEntryAtThisCandle = trade.entryTimeSec === c.time;
                                  const isExitAtThisCandle = trade.exitTimeSec === c.time;

                                  if (!isEntryAtThisCandle && !isExitAtThisCandle) return null;

                                  return (
                                    <g key={`trade-marker-${trade.id}-${tIdx}`} className="pointer-events-none select-none">
                                      {isEntryAtThisCandle && (
                                        <g>
                                          <circle
                                            cx={xVal}
                                            cy={`calc(${wickBot} + 10px)`}
                                            r="4"
                                            fill="#10b981"
                                            className="animate-pulse"
                                            opacity="0.8"
                                          />
                                          <rect
                                            x={`calc(${xVal} - 16px)`}
                                            y={`calc(${wickBot} + 7px)`}
                                            width="32"
                                            height="7"
                                            rx="1"
                                            fill="#064e3b"
                                            stroke="#10b981"
                                            strokeWidth="0.5"
                                          />
                                          <text
                                            x={xVal}
                                            y={`calc(${wickBot} + 13px)`}
                                            fill="#34d399"
                                            fontSize="5px"
                                            fontWeight="bold"
                                            fontFamily="monospace"
                                            textAnchor="middle"
                                          >
                                            B {trade.type}
                                          </text>
                                        </g>
                                      )}

                                      {isExitAtThisCandle && (
                                        <g>
                                          <circle
                                            cx={xVal}
                                            cy={`calc(${wickTop} - 10px)`}
                                            r="4"
                                            fill="#f43f5e"
                                            className="animate-pulse"
                                            opacity="0.8"
                                          />
                                          <rect
                                            x={`calc(${xVal} - 16px)`}
                                            y={`calc(${wickTop} - 15px)`}
                                            width="32"
                                            height="7"
                                            rx="1"
                                            fill="#5c071a"
                                            stroke="#f43f5e"
                                            strokeWidth="0.5"
                                          />
                                          <text
                                            x={xVal}
                                            y={`calc(${wickTop} - 9px)`}
                                            fill="#f87171"
                                            fontSize="5px"
                                            fontWeight="bold"
                                            fontFamily="monospace"
                                            textAnchor="middle"
                                          >
                                            EXIT
                                          </text>
                                        </g>
                                      )}
                                    </g>
                                  );
                                })}
                              </g>
                            );
                          })}
                        </>
                      );
                    })()}
                  </svg>
                )}
              </div>
            </div>

            {/* SIDE-BY-SIDE SPOT CE PE OPTION PREMIUM CHARTS */}
            {config.layout === "side-by-side" && (
              <div id="option-premium-duo-wrapper" className="grid grid-cols-1 md:grid-cols-2 gap-1.5 flex-1 select-none">
                {/* CE CONTRACT CHART */}
                <div id="ce-premium-chart" className="bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-3 flex flex-col justify-between overflow-hidden relative">
                  <div className="flex justify-between items-center border-b border-zinc-805 pb-1.5 mb-1.5 text-xs">
                    <span className="font-extrabold text-emerald-400 flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" /> ATM CALL CE PREMIUM ({atmStrike})
                    </span>
                    <span className="font-mono text-[9px] text-[#06b6d4]">9 EMA Trailing Lock</span>
                  </div>

                  {/* HIGH PERFORMANCE CE SVG CHART */}
                  <div className="flex-1 min-h-[140px] relative">
                    {displayCECandles.length === 0 ? (
                      <div className="absolute inset-0 flex items-center justify-center text-zinc-500 text-xs">Awaiting calculations...</div>
                    ) : (
                      <svg className="w-full h-full" style={{ overflow: "visible" }}>
                        {(() => {
                          const prices = displayCECandles.flatMap((c) => [c.high, c.low]);
                          const max = Math.max(...prices);
                          const min = Math.min(...prices);
                          const delta = max - min || 5;
                          const yYMax = max + delta * 0.05;
                          const yYMin = min - delta * 0.05;

                          const getX = (idx: number) => `${(idx / (displayCECandles.length - 1)) * 95}%`;
                          const getY = (price: number) => `${(1 - (price - yYMin) / (yYMax - yYMin)) * 90}%`;

                          return (
                            <>
                              {/* 9 EMA Underlay Line to respect 9 EMA Execution rule */}
                              <polyline
                                fill="none"
                                stroke="#06b6d4"
                                strokeWidth="1.2"
                                points={displayCECandles
                                  .map((c, idx) => c.ema ? `${(idx / (displayCECandles.length - 1)) * 95}%,${getY(c.ema)}` : "")
                                  .filter(Boolean)
                                  .join(" ")}
                              />

                              {/* 1-min option candle nodes */}
                              {displayCECandles.map((c, idx) => {
                                const rectGreen = c.close >= c.open;
                                const candleX = getX(idx);
                                const wickT = getY(c.high);
                                const wickB = getY(c.low);
                                const bodyT = getY(Math.max(c.open, c.close));
                                const bodyB = getY(Math.min(c.open, c.close));

                                return (
                                  <g key={`ce-cnd-${idx}`}>
                                    <line x1={candleX} y1={wickT} x2={candleX} y2={wickB} stroke={rectGreen ? "#10b981" : "#f43f5e"} strokeWidth="1" />
                                    <rect
                                      x={`calc(${candleX} - 3px)`}
                                      y={bodyT}
                                      width="6"
                                      height={`calc(${bodyB} - ${bodyT} + 1px)`}
                                      fill={rectGreen ? "#10b981" : "#f43f5e"}
                                      rx="0.5"
                                    />
                                  </g>
                                );
                              })}

                              {/* Horizontal current LTP line overlay */}
                              <line
                                x1="0%"
                                y1={getY(displayCECandles[displayCECandles.length - 1].close)}
                                x2="100%"
                                y2={getY(displayCECandles[displayCECandles.length - 1].close)}
                                stroke="#10b981"
                                strokeWidth="0.5"
                                strokeDasharray="2,2"
                              />
                            </>
                          );
                        })()}
                      </svg>
                    )}
                  </div>

                  <div className="flex justify-between items-center text-[10px] font-mono mt-2 pt-1 border-t border-zinc-800">
                    <span className="text-zinc-500">LTP Premium</span>
                    <span className="text-emerald-400 font-bold">₹{ceCandles[ceCandles.length - 1]?.close.toFixed(1)}</span>
                  </div>
                </div>

                {/* PE CONTRACT CHART */}
                <div id="pe-premium-chart" className="bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-3 flex flex-col justify-between overflow-hidden relative">
                  <div className="flex justify-between items-center border-b border-zinc-805 pb-1.5 mb-1.5 text-xs">
                    <span className="font-extrabold text-rose-400 flex items-center gap-1">
                      <TrendingDown className="h-3 w-3" /> ATM PUT PE PREMIUM ({atmStrike})
                    </span>
                    <span className="font-mono text-[9px] text-[#06b6d4]">9 EMA Trailing Lock</span>
                  </div>

                  {/* HIGH PERFORMANCE PE SVG CHART */}
                  <div className="flex-1 min-h-[140px] relative">
                    {displayPECandles.length === 0 ? (
                      <div className="absolute inset-0 flex items-center justify-center text-zinc-500 text-xs">Awaiting metrics...</div>
                    ) : (
                      <svg className="w-full h-full" style={{ overflow: "visible" }}>
                        {(() => {
                          const prices = displayPECandles.flatMap((c) => [c.high, c.low]);
                          const max = Math.max(...prices);
                          const min = Math.min(...prices);
                          const delta = max - min || 5;
                          const yYMax = max + delta * 0.05;
                          const yYMin = min - delta * 0.05;

                          const getX = (idx: number) => `${(idx / (displayPECandles.length - 1)) * 95}%`;
                          const getY = (price: number) => `${(1 - (price - yYMin) / (yYMax - yYMin)) * 90}%`;

                          return (
                            <>
                              {/* 9 EMA Underlay Line to respect 9 EMA Execution rule */}
                              <polyline
                                fill="none"
                                stroke="#06b6d4"
                                strokeWidth="1.2"
                                points={displayPECandles
                                  .map((c, idx) => c.ema ? `${(idx / (displayPECandles.length - 1)) * 95}%,${getY(c.ema)}` : "")
                                  .filter(Boolean)
                                  .join(" ")}
                              />

                              {/* 1-min option candle nodes */}
                              {displayPECandles.map((c, idx) => {
                                const rectGreen = c.close >= c.open;
                                const candleX = getX(idx);
                                const wickT = getY(c.high);
                                const wickB = getY(c.low);
                                const bodyT = getY(Math.max(c.open, c.close));
                                const bodyB = getY(Math.min(c.open, c.close));

                                return (
                                  <g key={`pe-cnd-${idx}`}>
                                    <line x1={candleX} y1={wickT} x2={candleX} y2={wickB} stroke={rectGreen ? "#10b981" : "#f43f5e"} strokeWidth="1" />
                                    <rect
                                      x={`calc(${candleX} - 3px)`}
                                      y={bodyT}
                                      width="6"
                                      height={`calc(${bodyB} - ${bodyT} + 1px)`}
                                      fill={rectGreen ? "#10b981" : "#f43f5e"}
                                      rx="0.5"
                                    />
                                  </g>
                                );
                              })}

                              {/* Horizontal current LTP line overlay */}
                              <line
                                x1="0%"
                                y1={getY(displayPECandles[displayPECandles.length - 1].close)}
                                x2="100%"
                                y2={getY(displayPECandles[displayPECandles.length - 1].close)}
                                stroke="#f43f5e"
                                strokeWidth="0.5"
                                strokeDasharray="2,2"
                              />
                            </>
                          );
                        })()}
                      </svg>
                    )}
                  </div>

                  <div className="flex justify-between items-center text-[10px] font-mono mt-2 pt-1 border-t border-zinc-800">
                    <span className="text-zinc-500">LTP Premium</span>
                    <span className="text-rose-400 font-bold">₹{peCandles[peCandles.length - 1]?.close.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* COLUMN 3: DEPTH BOOK & STRIKES CHAIN (3 cols) */}
          <section id="scalp-depth-panels" className="lg:col-span-3 flex flex-col gap-1.5">
            {/* LEVEL 2 REAL-TIME ORDER BOOK BAR DEPTH CHART */}
            <div id="l2-order-book" className="bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-3 flex flex-col justify-between overflow-hidden">
              <div>
                <dt className="text-[10px] text-zinc-400 font-bold uppercase tracking-wide flex items-center gap-1 border-b border-zinc-800/80 pb-1.5 mb-2">
                  <Database className="h-3.5 w-3.5 text-sky-400" /> Options Depth Book Level 2 (Bids vs Asks)
                </dt>

                {/* CE & PE Split lists preview */}
                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                  {/* CE ASKS & BIDS QUEUE */}
                  <div className="space-y-1.5">
                    <div className="text-[9px] font-extrabold text-emerald-400 border-b border-zinc-800 pb-0.5 text-center">CALLS (CE)</div>

                    {/* Bids queue lists (Green bars representing depth) */}
                    <div className="space-y-1">
                      {ceOrderBook.bids.slice(0, 4).map((bid, bId) => (
                        <div key={`ce-bid-${bId}`} className="relative h-4 flex items-center justify-between px-1 overflow-hidden rounded bg-emerald-950/5">
                          <div
                            className="absolute top-0 bottom-0 left-0 bg-emerald-500/10 z-0 transition-all duration-300"
                            style={{ width: `${bid.percentage}%` }}
                          />
                          <span className="text-emerald-400 font-semibold z-10">{bid.price.toFixed(1)}</span>
                          <span className="text-zinc-400 text-[9px] z-10">{bid.quantity}</span>
                        </div>
                      ))}
                    </div>

                    <div className="border-t border-zinc-900 my-1"></div>

                    {/* Asks queue lists (Red bars representing depth) */}
                    <div className="space-y-1">
                      {ceOrderBook.asks.slice(0, 4).map((ask, aId) => (
                        <div key={`ce-ask-${aId}`} className="relative h-4 flex items-center justify-between px-1 overflow-hidden rounded bg-rose-950/5">
                          <div
                            className="absolute top-0 bottom-0 right-0 bg-rose-500/10 z-0 transition-all duration-300"
                            style={{ width: `${ask.percentage}%` }}
                          />
                          <span className="text-rose-400 font-semibold z-10">{ask.price.toFixed(1)}</span>
                          <span className="text-zinc-400 text-[9px] z-10">{ask.quantity}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* PE ASKS & BIDS QUEUE */}
                  <div className="space-y-1.5">
                    <div className="text-[9px] font-extrabold text-rose-400 border-b border-zinc-800 pb-0.5 text-center">PUTS (PE)</div>

                    {/* Bids queue lists (Green bars representing depth) */}
                    <div className="space-y-1">
                      {peOrderBook.bids.slice(0, 4).map((bid, bId) => (
                        <div key={`pe-bid-${bId}`} className="relative h-4 flex items-center justify-between px-1 overflow-hidden rounded bg-emerald-950/5">
                          <div
                            className="absolute top-0 bottom-0 left-0 bg-emerald-500/10 z-0 transition-all duration-300"
                            style={{ width: `${bid.percentage}%` }}
                          />
                          <span className="text-emerald-400 font-semibold z-10">{bid.price.toFixed(1)}</span>
                          <span className="text-zinc-400 text-[9px] z-10">{bid.quantity}</span>
                        </div>
                      ))}
                    </div>

                    <div className="border-t border-zinc-900 my-1"></div>

                    {/* Asks queue list */}
                    <div className="space-y-1">
                      {peOrderBook.asks.slice(0, 4).map((ask, aId) => (
                        <div key={`pe-ask-${aId}`} className="relative h-4 flex items-center justify-between px-1 overflow-hidden rounded bg-rose-950/5">
                          <div
                            className="absolute top-0 bottom-0 right-0 bg-rose-500/10 z-0 transition-all duration-300"
                            style={{ width: `${ask.percentage}%` }}
                          />
                          <span className="text-rose-400 font-semibold z-10">{ask.price.toFixed(1)}</span>
                          <span className="text-zinc-400 text-[9px] z-10">{ask.quantity}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* DYNAMIC STRIKES CHAIN BOARD MATRIX */}
            <div id="strikes-board-panel" className="bg-[#0d0e12] border border-zinc-800/80 rounded-xl p-3 flex-1 flex flex-col justify-between overflow-hidden">
              <div>
                <dt className="text-[10px] text-zinc-400 font-bold uppercase tracking-wide flex items-center justify-between border-b border-zinc-800/80 pb-1.5 mb-2">
                  <span className="flex items-center gap-1">
                    <Sliders className="h-3.5 w-3.5 text-emerald-400" /> OPTION CHAIN (ATM ±3)
                  </span>
                  <span className="text-[9px] text-emerald-400 animate-pulse">L2 Tick Rate</span>
                </dt>

                {/* Strip titles */}
                <div className="grid grid-cols-5 text-[9px] text-zinc-500 font-bold uppercase tracking-wide text-center pb-1 border-b border-zinc-850">
                  <span>CE COI</span>
                  <span>CE Prem</span>
                  <span>STRIKE</span>
                  <span>PE Prem</span>
                  <span>PE COI</span>
                </div>

                {/* Chain item list */}
                <div className="space-y-1 max-h-[220px] overflow-y-auto mt-1 text-xs">
                  {strikes.map((st, sId) => {
                    const isATM = st.strike === atmStrike;
                    return (
                      <div
                        id={`strike-chain-row-${st.strike}`}
                        key={`chain-${sId}`}
                        className={`grid grid-cols-5 py-1 items-center text-center font-mono rounded cursor-pointer transition ${
                          isATM
                            ? "bg-zinc-800/70 border border-zinc-700/55 font-bold"
                            : "hover:bg-zinc-900 border border-transparent"
                        }`}
                      >
                        {/* CE COI */}
                        <span className="text-rose-400 text-[10px] truncate">
                          {Math.round(st.callCOI / 1000)}k
                        </span>

                        {/* CE Premium Cell with Hover (B)/(S) Quick Action buttons */}
                        <div id={`ce-prem-cell-${st.strike}`} className="relative h-6 flex items-center justify-center group">
                          {/* Default state: premium price */}
                          <div className="absolute inset-0 flex items-center justify-center group-hover:opacity-0 transition-all duration-150">
                            <span className="text-emerald-400 text-[11px] font-bold">
                              ₹{st.callPremium.toFixed(1)}
                            </span>
                          </div>
                          {/* Hover state: Buy (B) and Sell (S) triggers */}
                          <div className="absolute inset-0 flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-150 bg-[#14151b] border border-zinc-800 rounded">
                            <button
                              id={`hover-buy-ce-${st.strike}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                executeOrder("BUY", "CE", st.strike);
                              }}
                              className="bg-emerald-500 hover:bg-emerald-600 active:scale-95 text-black px-1.5 py-0.5 rounded text-[10px] font-extrabold shadow flex items-center justify-center cursor-pointer"
                              title={`Buy CE Strike ${st.strike}`}
                            >
                              B
                            </button>
                            <button
                              id={`hover-sell-ce-${st.strike}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                executeOrder("SELL", "CE", st.strike);
                              }}
                              className="bg-rose-500 hover:bg-rose-600 active:scale-95 text-white px-1.5 py-0.5 rounded text-[10px] font-extrabold shadow flex items-center justify-center cursor-pointer"
                              title={`Sell (Short) CE Strike ${st.strike}`}
                            >
                              S
                            </button>
                          </div>
                        </div>

                        {/* STRIKE PRICE */}
                        <span className={`text-[10px] font-bold ${isATM ? "text-white" : "text-zinc-200"}`}>
                          {st.strike}
                        </span>

                        {/* PE Premium Cell with Hover (B)/(S) Quick Action buttons */}
                        <div id={`pe-prem-cell-${st.strike}`} className="relative h-6 flex items-center justify-center group">
                          {/* Default state: premium price */}
                          <div className="absolute inset-0 flex items-center justify-center group-hover:opacity-0 transition-all duration-150">
                            <span className="text-rose-400 text-[11px] font-bold">
                              ₹{st.putPremium.toFixed(1)}
                            </span>
                          </div>
                          {/* Hover state: Buy (B) and Sell (S) triggers */}
                          <div className="absolute inset-0 flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-150 bg-[#14151b] border border-zinc-800 rounded">
                            <button
                              id={`hover-buy-pe-${st.strike}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                executeOrder("BUY", "PE", st.strike);
                              }}
                              className="bg-emerald-500 hover:bg-emerald-600 active:scale-95 text-black px-1.5 py-0.5 rounded text-[10px] font-extrabold shadow flex items-center justify-center cursor-pointer"
                              title={`Buy PE Strike ${st.strike}`}
                            >
                              B
                            </button>
                            <button
                              id={`hover-sell-pe-${st.strike}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                executeOrder("SELL", "PE", st.strike);
                              }}
                              className="bg-rose-500 hover:bg-rose-600 active:scale-95 text-white px-1.5 py-0.5 rounded text-[10px] font-extrabold shadow flex items-center justify-center cursor-pointer"
                              title={`Sell (Short) PE Strike ${st.strike}`}
                            >
                              S
                            </button>
                          </div>
                        </div>

                        {/* PE COI */}
                        <span className="text-emerald-400 text-[10px] truncate">
                          {Math.round(st.putCOI / 1000)}k
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Quick trade confirmation rules footer */}
              <div className="bg-[#12141c]/50 p-2 rounded-lg border border-zinc-805 text-[9px] text-zinc-500 mt-2 space-y-1">
                <div className="flex justify-between">
                  <span>9 EMA Break filter:</span>
                  <span className="text-zinc-400 font-bold">Automatic Veto</span>
                </div>
                <div className="flex justify-between">
                  <span>Min Spread limits:</span>
                  <span className="text-zinc-400 font-bold">Enabled</span>
                </div>
              </div>
            </div>
          </section>
        </main>
      )}

      {/* STRATEGY ALERT CONSOLE TERMINAL (Strictly following the specified pattern layout) */}
      <footer id="alert-console-terminal" className="bg-[#0b0c10] border-t border-zinc-800/80 p-3 max-h-[190px] overflow-y-auto flex flex-col justify-start">
        <div className="flex justify-between items-center mb-1.5 text-xs text-zinc-500 font-mono tracking-wide uppercase">
          <span className="font-bold flex items-center gap-1.5 text-zinc-400">
            <Activity className="h-4 w-4 text-emerald-400 animate-pulse" /> Real-time Alert Decoupling Engine
          </span>
          <span className="text-[10px]">MD BREAKOUT CONFIRMATIONS ACTIVE</span>
        </div>

        {/* Signals scrolling queue */}
        <div className="space-y-1.5 overflow-y-auto pr-1">
          {signals.length === 0 ? (
            <div className="text-center py-4 text-zinc-500 text-xs">
              Waiting for low-latency option market candle aggregations...
            </div>
          ) : (
            signals.slice(0, 15).map((sig, sigId) => {
              const bgClass =
                sig.tradingBias === TradingBias.HIGH_CONVICTION_BULLISH
                  ? "bg-[#0b1d12] border-emerald-500/25"
                  : sig.tradingBias === TradingBias.HIGH_CONVICTION_BEARISH
                  ? "bg-[#251010] border-rose-500/25"
                  : sig.tradingBias === TradingBias.HARD_EXIT
                  ? "bg-[#251025] border-pink-500/20"
                  : "bg-zinc-900 border-zinc-800/60";

              const badgeColorClass =
                sig.tradingBias === TradingBias.HIGH_CONVICTION_BULLISH
                  ? "bg-emerald-500 text-black"
                  : sig.tradingBias === TradingBias.HIGH_CONVICTION_BEARISH
                  ? "bg-rose-500 text-white"
                  : sig.tradingBias === TradingBias.HARD_EXIT
                  ? "bg-pink-500 text-white animate-pulse"
                  : "bg-zinc-700 text-zinc-200";

              return (
                <div
                  id={`alert-row-${sigId}`}
                  key={sigId}
                  className={`p-3 rounded-xl border text-[10px] font-mono leading-relaxed transition-all duration-300 ${bgClass}`}
                >
                  <p className="text-zinc-200 font-bold">
                    Timestamp: {sig.timestamp} | Day Regime: {sig.dayRegime} | Index tracked: {sig.indexTracked}
                  </p>
                  <p className="text-zinc-400 mt-0.5">
                    Index Spot: <strong className="text-zinc-100">{sig.indexSpot.toFixed(2)}</strong> | ATM Strike: <strong className="text-zinc-100">{sig.atmStrike}</strong> | Window Status: <strong className="text-amber-300">{sig.windowStatus}</strong>
                  </p>
                  <p className="text-zinc-400">
                    Current COI PCR: <strong className="text-zinc-100">{sig.currentCoiPcr}</strong> | Trend (last 30 mins): <strong className="text-zinc-100">{sig.trendLast30Min}</strong>
                  </p>
                  <p className="text-zinc-400">
                    Absolute OI Walls: <span className="text-rose-400 font-bold">{sig.absoluteOiWalls.callWallStrike} (Resistance)</span> vs <span className="text-emerald-400 font-bold">{sig.absoluteOiWalls.putWallStrike} (Support)</span>
                  </p>

                  {/* Confluence details wrapper row */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-x-3 gap-y-1 py-1 my-1 border-t border-b border-zinc-800 text-zinc-500">
                    <div>Structure: <span className="text-zinc-300 font-semibold">{sig.confluenceAnalysis.marketStructure}</span></div>
                    <div>Premium Swings: <span className="text-zinc-300 font-semibold">{sig.confluenceAnalysis.premiumSwings}</span></div>
                    <div>Arrival COI: <span className="text-zinc-305 font-semibold text-[9px]">{sig.confluenceAnalysis.arrivalCoiShift}</span></div>
                    <div>Context: <span className="text-zinc-300 font-semibold">{sig.confluenceAnalysis.institutionalContext}</span></div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded font-bold text-[9px] ${badgeColorClass}`}>
                      {sig.tradingBias}
                    </span>
                    <span className="text-white font-bold flex-1">{sig.action}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </footer>
    </div>
  );
}
