export enum InstrumentType {
  NIFTY = "NIFTY",
  BANKNIFTY = "BANKNIFTY",
}

export enum ExpiryRegime {
  STANDARD = "Standard Day",
  THURSDAY_EXPIRY = "Thursday Expiry Day",
}

export enum TradingBias {
  HIGH_CONVICTION_BULLISH = "HIGH-CONVICTION BULLISH",
  HIGH_CONVICTION_BEARISH = "HIGH-CONVICTION BEARISH",
  NEUTRAL = "NEUTRAL",
  GAMMA_LOCK = "GAMMA LOCK",
  HARD_EXIT = "HARD EXIT",
}

export interface Candlestick {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  oi?: number; // Open Interest underlay
  vwap?: number;
  ema?: number;
}

export type OptionType = "CE" | "PE";

export interface OptionStrikeData {
  strike: number;
  callOI: number;
  callCOI: number;
  callPremium: number;
  putOI: number;
  putCOI: number;
  putPremium: number;
  callVolume: number;
  putVolume: number;
}

export interface MarketStructure {
  highs: { price: number; idx: number; timestamp: number; retested: boolean }[];
  lows: { price: number; idx: number; timestamp: number; retested: boolean }[];
  orderBlocks: {
    priceStart: number;
    priceEnd: number;
    idx: number;
    type: "bullish" | "bearish";
    strength: number;
    isMitigated: boolean;
  }[];
  fairValueGaps: {
    top: number;
    bottom: number;
    idx: number;
    type: "bullish" | "bearish";
    isFilled: boolean;
  }[];
}

export interface OrderBookLevel {
  price: number;
  quantity: number;
  cumulativeDepth: number;
  percentage: number;
}

export interface OrderBook {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  maxQuantity: number;
}

export interface Position {
  id: string;
  instrument: InstrumentType;
  type: "CE" | "PE";
  strike: number;
  entryPrice: number;
  quantity: number;
  currentPrice: number;
  stopLoss?: number;
  takeProfit?: number;
  pnl: number;
  timestamp: string;
  side?: "BUY" | "SELL";
  entrySpot?: number;
  exitSpot?: number;
  entryTimeSec?: number;
  exitTimeSec?: number;
  exitPrice?: number;
  exitReason?: string;
  status?: "ACTIVE" | "CLOSED";
}

export interface TradeSignal {
  timestamp: string;
  dayRegime: ExpiryRegime;
  indexTracked: InstrumentType;
  indexSpot: number;
  atmStrike: number;
  windowStatus: "Aligned" | "Shifted" | "Stabilizing";
  currentCoiPcr: number;
  trendLast30Min: "Rising" | "Falling" | "Flat";
  absoluteOiWalls: {
    callWallStrike: number;
    callWallVolume: number;
    putWallStrike: number;
    putWallVolume: number;
  };
  confluenceAnalysis: {
    marketStructure: "Higher Highs / Lower Lows" | "Lower Highs / Lower Lows" | "Ranging";
    premiumSwings: "CE Breakout" | "PE Breakout" | "Compression";
    arrivalCoiShift: "Call Writing Spike at Resistance" | "Put Writing at Support" | "None";
    institutionalContext: "Put Unwinding" | "Call Unwinding" | "Short Build-up" | "Long Liquidation";
  };
  tradingBias: TradingBias;
  action: string;
  isRead: boolean;
}

export interface WorkspaceConfig {
  layout: "single" | "side-by-side" | "multi-monitor";
  isExpiryDay: boolean;
  oneClickEnabled: boolean;
  timeframeLock: "1m" | "5m" | "15m";
  speedMultiplier: number; // For demo/simulation speed
  isHotKeysEnabled: boolean;
}
