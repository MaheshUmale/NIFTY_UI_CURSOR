import {
  InstrumentType,
  ExpiryRegime,
  TradingBias,
  Candlestick,
  OptionStrikeData,
  MarketStructure,
  OrderBook,
  Position,
  TradeSignal,
} from "../types";

// Dynamic Spot Initializers
const SPOT_INIT = {
  [InstrumentType.NIFTY]: 22450.5,
  [InstrumentType.BANKNIFTY]: 48150.25,
};

// Tick Interval in index units
const VOLATILITY_INIT = {
  [InstrumentType.NIFTY]: 3.5,
  [InstrumentType.BANKNIFTY]: 12.0,
};

export class MarketEngine {
  public instrument: InstrumentType = InstrumentType.NIFTY;
  public regime: ExpiryRegime = ExpiryRegime.STANDARD;
  public spotPrice: number = SPOT_INIT[InstrumentType.NIFTY];
  public atmStrike: number = 22450;

  // Historical 1-Minute Candlesticks
  public spotCandles: Candlestick[] = [];
  public ceCandles: Candlestick[] = [];
  public peCandles: Candlestick[] = [];

  // Strike Chain Data (ATM ± 3 = 7 Strikes)
  public strikeChain: OptionStrikeData[] = [];
  public windowStatus: "Aligned" | "Shifted" | "Stabilizing" = "Aligned";
  private stabilizingTimeLeft: number = 0; // seconds

  // Level 2 Order Books
  public ceOrderBook: OrderBook = { bids: [], asks: [], maxQuantity: 1 };
  public peOrderBook: OrderBook = { bids: [], asks: [], maxQuantity: 1 };

  // UI / Signal State
  public signalsLog: TradeSignal[] = [];
  private baseTimestamp: number = Math.floor(Date.now() / 1000) - 300 * 60; // 5 hours ago

  constructor(instrument: InstrumentType, regime: ExpiryRegime) {
    this.instrument = instrument;
    this.regime = regime;
    this.spotPrice = SPOT_INIT[instrument];
    this.atmStrike = this.calculateATM(this.spotPrice);
    this.seedHistory();
    this.updateStrikeChain();
    this.generateOrderBooks();
  }

  // Calculate ATM Strike
  public calculateATM(price: number): number {
    const step = this.instrument === InstrumentType.NIFTY ? 50 : 100;
    return Math.round(price / step) * step;
  }

  // Generate historical pre-seed candles
  public seedHistory() {
    this.spotCandles = [];
    this.ceCandles = [];
    this.peCandles = [];
    let currentSpot = this.spotPrice - 80; // Start lower for upward trend with Pullbacks
    let baseTime = this.baseTimestamp;

    const step = this.instrument === InstrumentType.NIFTY ? 50 : 100;

    for (let i = 0; i < 120; i++) {
      baseTime += 60; // plus 1 minute
      // Realistically model some random walk with positive-bias trend
      const change = (Math.sin(i / 10) * 8) + (Math.random() - 0.45) * 6;
      const open = currentSpot;
      const close = currentSpot + change;
      const high = Math.max(open, close) + Math.random() * 3;
      const low = Math.min(open, close) - Math.random() * 3;
      currentSpot = close;

      this.spotCandles.push({
        time: baseTime,
        open,
        high,
        low,
        close,
        volume: 15000 + Math.floor(Math.random() * 10000),
      });

      // ATM strikes option pricing approximation
      // Pricing CE and PE according to distance from current spot S to option strike K
      const atmK = this.atmStrike;
      const distance = currentSpot - atmK;

      // CE and PE premium approximations with added volatility premium
      const ceClose = Math.max(10, 100 + distance * 0.6 + Math.sin(i / 15) * 8 + Math.random() * 2);
      const peClose = Math.max(10, 90 - distance * 0.5 + Math.cos(i / 15) * 8 + Math.random() * 2);

      this.ceCandles.push({
        time: baseTime,
        open: ceClose - (change * 0.4),
        high: Math.max(ceClose, ceClose - (change * 0.4)) + Math.random() * 1.5,
        low: Math.min(ceClose, ceClose - (change * 0.4)) - Math.random() * 1.5,
        close: ceClose,
        volume: 8000 + Math.floor(Math.random() * 10000),
      });

      this.peCandles.push({
        time: baseTime,
        open: peClose + (change * 0.3),
        high: Math.max(peClose, peClose + (change * 0.3)) + Math.random() * 1.5,
        low: Math.min(peClose, peClose + (change * 0.3)) - Math.random() * 1.5,
        close: peClose,
        volume: 7500 + Math.floor(Math.random() * 12000),
      });
    }

    this.spotPrice = currentSpot;
    this.calculateIndicators();
  }

  // Calculate moving averages & VWAP and save to historic candles
  private calculateIndicators() {
    this.computeSeriesStats(this.spotCandles);
    this.computeSeriesStats(this.ceCandles);
    this.computeSeriesStats(this.peCandles);
  }

  private computeSeriesStats(series: Candlestick[]) {
    let cumVolume = 0;
    let cumPV = 0;
    for (let i = 0; i < series.length; i++) {
      const candle = series[i];
      const typicalPrice = (candle.high + candle.low + candle.close) / 3;
      cumVolume += candle.volume;
      cumPV += typicalPrice * candle.volume;
      candle.vwap = Math.round((cumPV / cumVolume) * 100) / 100;

      // Simple 9 Period EMA
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
  }

  // Re-build standard strike chain (ATM ± 3 strikes)
  public updateStrikeChain() {
    const step = this.instrument === InstrumentType.NIFTY ? 50 : 100;
    const baseStrike = this.atmStrike;
    const strikes = [
      baseStrike - 3 * step,
      baseStrike - 2 * step,
      baseStrike - step,
      baseStrike,
      baseStrike + step,
      baseStrike + 2 * step,
      baseStrike + 3 * step,
    ];

    const spot = this.spotPrice;

    this.strikeChain = strikes.map((strike) => {
      // Model realistic institutional OI base numbers
      // Put OI is heavier at lower strikes, Call OI is heavier at higher strikes
      const diff = spot - strike;
      const baseCallOI = Math.max(12000, 150000 - diff * 300 + Math.random() * 10000);
      const basePutOI = Math.max(10000, 140000 + diff * 280 + Math.random() * 10000);

      // COI (Change in Open interest) models current day writing activity
      const callCOI = Math.max(-5000, 30000 - diff * 80 + Math.random() * 5000);
      const putCOI = Math.max(-4000, 28000 + diff * 70 + Math.random() * 5000);

      // Dynamic premium models
      const cePremium = Math.max(2, 100 + (spot - strike) * 0.6 + Math.random() * 3);
      const pePremium = Math.max(2, 90 + (strike - spot) * 0.5 + Math.random() * 3);

      return {
        strike,
        callOI: Math.floor(baseCallOI),
        callCOI: Math.floor(callCOI),
        callPremium: Math.round(cePremium * 10) / 10,
        putOI: Math.floor(basePutOI),
        putCOI: Math.floor(putCOI),
        putPremium: Math.round(pePremium * 10) / 10,
        callVolume: Math.floor(baseCallOI * 0.12),
        putVolume: Math.floor(basePutOI * 0.14),
      };
    });
  }

  // Generate real-time simulation tick updates
  public triggerTick(customDeltaPercentClose: number = 0): {
    spotTick: number;
    cePrice: number;
    pePrice: number;
    oiPcr: number;
  } {
    const step = this.instrument === InstrumentType.NIFTY ? 50 : 100;
    const tickRange = VOLATILITY_INIT[this.instrument];

    // Decrement stabilizing timer
    if (this.stabilizingTimeLeft > 0) {
      this.stabilizingTimeLeft -= 1;
      if (this.stabilizingTimeLeft <= 0) {
        this.windowStatus = "Aligned";
      }
    }

    // Dynamic price walk
    const spotChange = (Math.random() - 0.495) * tickRange + customDeltaPercentClose;
    this.spotPrice = Math.round((this.spotPrice + spotChange) * 100) / 100;

    // Shift ATM Strike check
    const currentATM = this.calculateATM(this.spotPrice);
    if (currentATM !== this.atmStrike) {
      // Midpoint rule violation triggers shifting block
      this.atmStrike = currentATM;
      this.windowStatus = "Stabilizing";
      this.stabilizingTimeLeft = 15; // Set 15 mock seconds/intervals of stability check [WINDOW SHIFTING]
      this.updateStrikeChain();
    }

    // Tick current option prices relative to ATM Strike
    const ceBreakoutChance = Math.random();
    const ceShift = (this.spotPrice - this.atmStrike) * 0.6 + (ceBreakoutChance > 0.95 ? 12 : 0);
    const peShift = (this.atmStrike - this.spotPrice) * 0.5 + (ceBreakoutChance < 0.05 ? 10 : 0);

    const activeCEPrice = Math.max(3, 110 + ceShift + (Math.random() - 0.5) * 1.5);
    const activePEPrice = Math.max(3, 95 + peShift + (Math.random() - 0.5) * 1.5);

    // Update current active minute candle limits
    this.updateCandleTick(this.spotCandles, this.spotPrice);
    this.updateCandleTick(this.ceCandles, activeCEPrice);
    this.updateCandleTick(this.peCandles, activePEPrice);

    // Update strike chain option premiums in real time
    this.strikeChain.forEach((ch) => {
      const strikeDiff = this.spotPrice - ch.strike;
      ch.callPremium = Math.max(1, Math.round((110 + strikeDiff * 0.6 + (Math.random() - 0.5) * 1) * 10) / 10);
      ch.putPremium = Math.max(1, Math.round((95 - strikeDiff * 0.5 + (Math.random() - 0.5) * 1) * 10) / 10);

      // Micro shifts in Open Interest to emulate institutional hedging/scrambling
      if (Math.random() > 0.4) {
        const oiTick = Math.floor((Math.random() - 0.4) * 800);
        if (Math.random() > 0.5) {
          ch.callOI += oiTick;
          ch.callCOI += oiTick;
        } else {
          ch.putOI += oiTick;
          ch.putCOI += oiTick;
        }
      }
    });

    // Recompute Orderbooks & PCR
    this.generateOrderBooks(activeCEPrice, activePEPrice);
    const pcr = this.getCOIPCR();

    return {
      spotTick: this.spotPrice,
      cePrice: activeCEPrice,
      pePrice: activePEPrice,
      oiPcr: pcr,
    };
  }

  // Live orderbook Level 2 generator
  private generateOrderBooks(ceLTP?: number, peLTP?: number) {
    const cePrice = ceLTP || this.ceCandles[this.ceCandles.length - 1].close;
    const pePrice = peLTP || this.peCandles[this.peCandles.length - 1].close;

    this.ceOrderBook = this.buildL2Depth(cePrice);
    this.peOrderBook = this.buildL2Depth(pePrice);
  }

  private buildL2Depth(ltp: number): OrderBook {
    const bids: any[] = [];
    const asks: any[] = [];
    let maxQty = 0;

    // Create 10 Level Deep matching queue
    for (let i = 1; i <= 10; i++) {
      const bidPrice = Math.round((ltp - i * 0.05) * 100) / 100;
      const askPrice = Math.round((ltp + i * 0.05) * 100) / 100;

      // Realistic volumes (higher volumes near the spread)
      const bidQty = Math.floor((15 - i) * (200 + Math.random() * 400));
      const askQty = Math.floor((15 - i) * (180 + Math.random() * 420));

      bids.push({ price: bidPrice, quantity: bidQty, cumulativeDepth: 0, percentage: 0 });
      asks.push({ price: askPrice, quantity: askQty, cumulativeDepth: 0, percentage: 0 });

      maxQty = Math.max(maxQty, bidQty, askQty);
    }

    // Calc cum depths
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
    asks.forEach((a) => (a.percentage = Math.round((a.quantity / maxQty) * 100)));

    return { bids, asks, maxQuantity: maxQty };
  }

  private updateCandleTick(series: Candlestick[], currentVal: number) {
    if (series.length === 0) return;
    const lastIdx = series.length - 1;
    const candle = series[lastIdx];

    // Tick OHLC update
    candle.high = Math.max(candle.high, currentVal);
    candle.low = Math.min(candle.low, currentVal);
    candle.close = currentVal;
    candle.volume += Math.floor(Math.random() * 50);

    // Accumulate custom indicator limits
    const typicalPrice = (candle.high + candle.low + candle.close) / 3;
    candle.vwap = Math.round((((candle.vwap || candle.close) * 2000 + typicalPrice * 50) / 2050) * 100) / 100;
  }

  // Create absolute boundary for 1-minute candle roll-overs
  public rollMinute() {
    const lastSpot = this.spotCandles[this.spotCandles.length - 1];
    const lastCE = this.ceCandles[this.ceCandles.length - 1];
    const lastPE = this.peCandles[this.peCandles.length - 1];

    const nextTime = lastSpot.time + 60;

    this.spotCandles.push({
      time: nextTime,
      open: lastSpot.close,
      high: lastSpot.close,
      low: lastSpot.close,
      close: lastSpot.close,
      volume: 0,
    });

    this.ceCandles.push({
      time: nextTime,
      open: lastCE.close,
      high: lastCE.close,
      low: lastCE.close,
      close: lastCE.close,
      volume: 0,
    });

    this.peCandles.push({
      time: nextTime,
      open: lastPE.close,
      high: lastPE.close,
      low: lastPE.close,
      close: lastPE.close,
      volume: 0,
    });

    // Clean historical index size length to maintain high UI rendering performance (keep ~200 candles)
    if (this.spotCandles.length > 200) {
      this.spotCandles.shift();
      this.ceCandles.shift();
      this.peCandles.shift();
    }

    this.calculateIndicators();
    this.checkForSignalsAndAlerts();
  }

  // Get current Change in Open Interest Put-Call Ratio
  public getCOIPCR(): number {
    let sumPutCOI = 0;
    let sumCallCOI = 0;

    this.strikeChain.forEach((ch) => {
      sumPutCOI += Math.max(0, ch.putCOI);
      sumCallCOI += Math.max(0, ch.callCOI);
    });

    if (sumCallCOI === 0) return 1.0;
    const ratio = sumPutCOI / sumCallCOI;
    return Math.round(ratio * 100) / 100;
  }

  // Automated Technical Analysis for Market Structure / Liquidity Zones
  public getMarketStructure(): MarketStructure {
    const highs: any[] = [];
    const lows: any[] = [];
    const orderBlocks: any[] = [];
    const fairValueGaps: any[] = [];

    const candles = this.spotCandles;
    const len = candles.length;

    // Detect structural Swing points over 5-candle windows
    for (let i = 2; i < len - 2; i++) {
      const cCurrent = candles[i];
      const prev1 = candles[i - 1];
      const prev2 = candles[i - 2];
      const next1 = candles[i + 1];
      const next2 = candles[i + 2];

      const isSwingHigh =
        cCurrent.high > prev1.high &&
        cCurrent.high > prev2.high &&
        cCurrent.high > next1.high &&
        cCurrent.high > next2.high;

      const isSwingLow =
        cCurrent.low < prev1.low &&
        cCurrent.low < prev2.low &&
        cCurrent.low < next1.low &&
        cCurrent.low < next2.low;

      if (isSwingHigh) {
        highs.push({ price: cCurrent.high, idx: i, timestamp: cCurrent.time, retested: false });
      }
      if (isSwingLow) {
        lows.push({ price: cCurrent.low, idx: i, timestamp: cCurrent.time, retested: false });
      }

      // Automatically identify Fair Value Gaps (FVG)
      // Standard FVG is the unfilled gap between candles i-1 low and candle i+1 high (or vice-versa for bearish)
      if (i > 1 && i < len - 1) {
        const preCandle = candles[i - 1];
        const postCandle = candles[i + 1];

        // Bullish FVG
        if (postCandle.low > preCandle.high && candles[i].close > candles[i].open) {
          fairValueGaps.push({
            top: postCandle.low,
            bottom: preCandle.high,
            idx: i,
            type: "bullish",
            isFilled: candles[len - 1].close < preCandle.high,
          });
        }
        // Bearish FVG
        else if (postCandle.high < preCandle.low && candles[i].close < candles[i].open) {
          fairValueGaps.push({
            top: preCandle.low,
            bottom: postCandle.high,
            idx: i,
            type: "bearish",
            isFilled: candles[len - 1].close > preCandle.low,
          });
        }
      }
    }

    // Identify Order Blocks (OB) - the last counter-trend candle before an aggressive expansion breakout
    for (let i = 3; i < len - 3; i++) {
      const candle = candles[i];
      // Bullish OB: Bearish candle followed by 3 aggressive green candles
      if (
        candle.close < candle.open &&
        candles[i + 1].close > candles[i + 1].open &&
        candles[i + 2].close > candles[i + 2].open &&
        candles[i + 3].close > candles[i + 3].open &&
        candles[i + 3].close > candle.high + 10
      ) {
        orderBlocks.push({
          priceStart: candle.low,
          priceEnd: candle.high,
          idx: i,
          type: "bullish",
          strength: 3,
          isMitigated: candles[len - 1].close < candle.low,
        });
      }
      // Bearish OB: Bullish candle followed by 3 aggressive red candles
      else if (
        candle.close > candle.open &&
        candles[i + 1].close < candles[i + 1].open &&
        candles[i + 2].close < candles[i + 2].open &&
        candles[i + 3].close < candles[i + 3].open &&
        candles[i + 3].close < candle.low - 10
      ) {
        orderBlocks.push({
          priceStart: candle.high,
          priceEnd: candle.low,
          idx: i,
          type: "bearish",
          strength: 3,
          isMitigated: candles[len - 1].close > candle.high,
        });
      }
    }

    return {
      highs: highs.slice(-5), // Keep last 5
      lows: lows.slice(-5),
      orderBlocks: orderBlocks.slice(-3),
      fairValueGaps: fairValueGaps.slice(-3),
    };
  }

  // Signal Evaluation Logic adhering strictly to Unified Strategy Document
  public checkForSignalsAndAlerts() {
    const pcr = this.getCOIPCR();
    const expiry = this.regime;
    const step = this.instrument === InstrumentType.NIFTY ? 50 : 100;

    // Last 30 mins PCR tendency estimation
    const spotCandlesCount = this.spotCandles.length;
    let trend: "Rising" | "Falling" | "Flat" = "Flat";

    if (spotCandlesCount > 30) {
      // Simulate historical trends
      const recent = pcr;
      const prior = 0.95 + Math.sin(spotCandlesCount / 20) * 0.15;
      const difference = recent - prior;
      trend = difference > 0.05 ? "Rising" : difference < -0.05 ? "Falling" : "Flat";
    }

    // Walls based on Strike Chain largest Open Interests
    let maxCallOIStrike = this.atmStrike + step;
    let maxCallOIVal = 0;
    let maxPutOIStrike = this.atmStrike - step;
    let maxPutOIVal = 0;

    this.strikeChain.forEach((ch) => {
      if (ch.callOI > maxCallOIVal) {
        maxCallOIVal = ch.callOI;
        maxCallOIStrike = ch.strike;
      }
      if (ch.putOI > maxPutOIVal) {
        maxPutOIVal = ch.putOI;
        maxPutOIStrike = ch.strike;
      }
    });

    // 3-Layer Confluence Analyzer
    let marketStructure: "Higher Highs / Lower Lows" | "Lower Highs / Lower Lows" | "Ranging" = "Ranging";
    const structures = this.getMarketStructure();
    if (structures.highs.length > 1 && structures.lows.length > 1) {
      const lastHigh = structures.highs[structures.highs.length - 1].price;
      const prevHigh = structures.highs[structures.highs.length - 2].price;
      const lastLow = structures.lows[structures.lows.length - 1].price;
      const prevLow = structures.lows[structures.lows.length - 2].price;

      if (lastHigh > prevHigh && lastLow > prevLow) {
        marketStructure = "Higher Highs / Lower Lows"; // Bullish structure notation as requested
      } else if (lastHigh < prevHigh && lastLow < prevLow) {
        marketStructure = "Lower Highs / Lower Lows";
      }
    }

    // Option Premium Swing Breakdown
    let premiumSwings: "CE Breakout" | "PE Breakout" | "Compression" = "Compression";
    const lastCEPrice = this.ceCandles[this.ceCandles.length - 1].close;
    const lastPEPrice = this.peCandles[this.peCandles.length - 1].close;

    if (lastCEPrice > 130 && pcr > 1.1) {
      premiumSwings = "CE Breakout";
    } else if (lastPEPrice > 115 && pcr < 0.8) {
      premiumSwings = "PE Breakout";
    }

    // COI Shifts at Resistance/Support
    let arrivalCoiShift: "Call Writing Spike at Resistance" | "Put Writing at Support" | "None" = "None";
    if (Math.abs(this.spotPrice - maxCallOIStrike) < 10) {
      arrivalCoiShift = "Call Writing Spike at Resistance";
    } else if (Math.abs(this.spotPrice - maxPutOIStrike) < 10) {
      arrivalCoiShift = "Put Writing at Support";
    }

    // Dynamic Context Builder
    let institutionalContext: "Put Unwinding" | "Call Unwinding" | "Short Build-up" | "Long Liquidation" = "Short Build-up";
    if (pcr > 1.3 && trend === "Rising") {
      institutionalContext = "Put Unwinding"; // Squeezing shorts
    } else if (pcr < 0.7 && trend === "Falling") {
      institutionalContext = "Call Unwinding";
    } else if (pcr >= 0.8 && pcr <= 1.2) {
      institutionalContext = "Short Build-up";
    } else {
      institutionalContext = "Long Liquidation";
    }

    // Define Directional Bias
    let bias = TradingBias.NEUTRAL;
    let action = "No Actions - PCR indices remain within standard neutral zones. Watch volume levels.";

    // Threshold boundaries optimized with Expiry Mode Scaling
    const isExpiry = expiry === ExpiryRegime.THURSDAY_EXPIRY;
    const bullTrigger = isExpiry ? 1.4 : 1.2;
    const bearTrigger = isExpiry ? 0.6 : 0.8;

    // Check European Window Veto
    const date = new Date();
    const currHour = date.getUTCHours() + 5; // offset IST
    const currMin = date.getUTCMinutes() + 30;
    const isLunchHour = currHour === 12 && currMin >= 30; // 12:30 PM IST European Open

    // Check Thursday Expiry Gamma Lock
    const isGammaLockTime = isExpiry && currHour >= 13 && currMin >= 30; // Post 1:30 PM Expiry

    if (isGammaLockTime) {
      bias = TradingBias.GAMMA_LOCK;
      action = "[EXPIRY GAMMA FLIP - EXECUTION SUSPENDED] Negligible premium scales detected. Unwinding locks active.";
    } else if (isLunchHour) {
      bias = TradingBias.NEUTRAL;
      action = "MONITOR WINDOW - European Fund flows active. PCR stabilizing filters enforced.";
    } else if (pcr > bullTrigger) {
      // Confirm with 3-layer confluence!
      const isStructureAlign = marketStructure === "Higher Highs / Lower Lows";
      const isPremiumSwingAlign = premiumSwings === "CE Breakout";

      if (isStructureAlign && isPremiumSwingAlign) {
        bias = TradingBias.HIGH_CONVICTION_BULLISH;
        action = `ENTER LONG OPTION SCALP (Buy ${this.atmStrike} CE) above 1m 9 EMA support. Target absolute Spot resistance Wall at ${maxCallOIStrike}.`;
      } else {
        bias = TradingBias.NEUTRAL;
        action = `PCR suggests Bullish pressure (${pcr}), but awaiting Layer A structural or Layer B premium breakout confluence alignment.`;
      }
    } else if (pcr < bearTrigger) {
      const isStructureAlign = marketStructure === "Lower Highs / Lower Lows";
      const isPremiumSwingAlign = premiumSwings === "PE Breakout";

      if (isStructureAlign && isPremiumSwingAlign) {
        bias = TradingBias.HIGH_CONVICTION_BEARISH;
        action = `ENTER SHORT OPTION SCALP (Buy ${this.atmStrike} PE) above 1m 9 EMA. Target structural Spot support Wall at ${maxPutOIStrike}.`;
      } else {
        bias = TradingBias.NEUTRAL;
        action = `PCR indicates Bearish pressure (${pcr}), but awaiting matching Confluence parameters. Stay fluid.`;
      }
    }

    // Trap Check: Price-OI Divergence Filter (Trap Check)
    const lastSpotClose = this.spotCandles[this.spotCandles.length - 1].close;
    const priorSpotClose = this.spotCandles[Math.max(0, this.spotCandles.length - 5)].close;
    const spotRising = lastSpotClose > priorSpotClose;

    if (spotRising && pcr < bearTrigger) {
      bias = TradingBias.HARD_EXIT;
      action = "RETAIL BULL TRAP DETECTED. Price rising while COI PCR dropping. Exit Call longs immediately.";
    } else if (!spotRising && pcr > bullTrigger) {
      bias = TradingBias.HARD_EXIT;
      action = "SHORT TRAP DETECTED! Option writers selling Calls. Spot range flattening. Pull Put longs.";
    }

    // Format final alert message according to standard format
    const timestamp = new Date().toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });

    const newSignal: TradeSignal = {
      timestamp,
      dayRegime: expiry,
      indexTracked: this.instrument,
      indexSpot: this.spotPrice,
      atmStrike: this.atmStrike,
      windowStatus: this.windowStatus,
      currentCoiPcr: pcr,
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

    // Prepend new signals to the visual log
    this.signalsLog.unshift(newSignal);

    // Limit log length to avoid excessive states (keep 50)
    if (this.signalsLog.length > 50) {
      this.signalsLog.pop();
    }
  }

  // Helper to calculate analytical gamma for a strike using Black-Scholes model approximation
  public calculateGammaValue(S: number, K: number, T: number, sigma: number, r: number = 0.07): number {
    if (S <= 0 || K <= 0 || T <= 0 || sigma <= 0) return 0;
    try {
      const d1 = (Math.log(S / K) + (r + (sigma * sigma) / 2) * T) / (sigma * Math.sqrt(T));
      const pdf = Math.exp(-0.5 * d1 * d1) / Math.sqrt(2 * Math.PI);
      return pdf / (S * sigma * Math.sqrt(T));
    } catch {
      return 0;
    }
  }

  // Retrieve Net Gamma Exposure Profile across the current strike chain (ATM ± 3)
  public getGEXProfile() {
    // Standard Days to Expiry (DTE) options approximation in fractional years
    const T = this.regime === ExpiryRegime.THURSDAY_EXPIRY ? 0.25 / 365 : 2.0 / 365;
    const sigma = this.instrument === InstrumentType.NIFTY ? 0.15 : 0.22;
    const spot = this.spotPrice;

    return this.strikeChain.map((st) => {
      const gamma = this.calculateGammaValue(spot, st.strike, T, sigma);
      // GEX in Index Price units per 1% move of the spot index
      // Net GEX = (Call_gamma * Call_OI) - (Put_gamma * Put_OI)
      // Scaled by 100 for visual chart representation
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
  }

  // Scan and detect exact spot coordinate where Net Market GEX crosses zero (Zero-Gamma Flip Level)
  public getVolatilityTrigger(): number {
    const step = this.instrument === InstrumentType.NIFTY ? 50 : 100;
    const baseStrike = this.atmStrike;
    let bestSpot = this.spotPrice;
    let minAbsNetGEX = Infinity;

    // Scan price spectrum around ATM strike with fine granularity (every 1 unit of index)
    const T = this.regime === ExpiryRegime.THURSDAY_EXPIRY ? 0.25 / 365 : 2.0 / 365;
    const sigma = this.instrument === InstrumentType.NIFTY ? 0.15 : 0.22;

    for (let testSpot = baseStrike - 4 * step; testSpot <= baseStrike + 4 * step; testSpot += 1) {
      let gexSum = 0;
      this.strikeChain.forEach((st) => {
        const gamma = this.calculateGammaValue(testSpot, st.strike, T, sigma);
        gexSum += (gamma * st.callOI) - (gamma * st.putOI);
      });

      const absGexSum = Math.abs(gexSum);
      if (absGexSum < minAbsNetGEX) {
        minAbsNetGEX = absGexSum;
        bestSpot = testSpot;
      }
    }
    return Math.round(bestSpot * 100) / 100;
  }

  // Overwrite local simulation state with real-time external Python/API data feed
  public updateExternalData(
    spotPrice: number,
    strikeChain: OptionStrikeData[],
    spotCandles?: Candlestick[],
    ceCandles?: Candlestick[],
    peCandles?: Candlestick[]
  ) {
    this.spotPrice = spotPrice;
    this.atmStrike = this.calculateATM(spotPrice);
    this.strikeChain = strikeChain;
    if (spotCandles && spotCandles.length > 0) this.spotCandles = spotCandles;
    if (ceCandles && ceCandles.length > 0) this.ceCandles = ceCandles;
    if (peCandles && peCandles.length > 0) this.peCandles = peCandles;

    // Refresh calculations based on updated values
    this.generateOrderBooks();
  }
}
