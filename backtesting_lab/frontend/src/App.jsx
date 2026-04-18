import React, { useState, useEffect } from 'react';
import { api } from './api';
import { 
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, ComposedChart
} from 'recharts';
import { 
  LayoutDashboard, History, Wallet, Briefcase, HelpCircle, LogOut, 
  Search, Bell, TrendingUp, TrendingDown, Activity, BrainCircuit,
  Settings, ShieldCheck, ChevronDown, Filter, Zap, Globe
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const SidebarItem = ({ icon: Icon, label, active = false }) => (
  <div className={cn(
    "flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all duration-200 group",
    active ? "bg-emerald-500/10 text-emerald-400" : "text-gray-400 hover:bg-gray-800 hover:text-white"
  )}>
    <Icon size={20} className={cn(active ? "text-emerald-400" : "group-hover:text-white")} />
    <span className="font-medium text-sm">{label}</span>
  </div>
);

const MetricCard = ({ label, value, delta, isPositive = true }) => (
  <div className="bg-[#161a23] border border-gray-800 p-5 rounded-2xl hover:border-emerald-500/40 transition-all duration-300">
    <p className="text-gray-400 text-xs uppercase tracking-wider mb-2">{label}</p>
    <div className="flex items-end justify-between">
      <h3 className="text-2xl font-bold text-white font-mono">{value}</h3>
      <span className={cn(
        "text-xs font-semibold px-2 py-1 rounded-md",
        isPositive ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
      )}>
        {delta}
      </span>
    </div>
  </div>
);

const MiniTicker = ({ ticker, sparkline }) => (
  <div className="bg-[#161a23] border border-gray-800 p-4 rounded-xl relative overflow-hidden group hover:border-emerald-500/30 transition-all">
    <div className="flex justify-between items-start mb-2">
      <div>
        <h4 className="text-white font-bold">{ticker.symbol}</h4>
        <p className="text-gray-500 text-[10px] uppercase">{ticker.name}</p>
      </div>
      <div className={cn("text-xs font-bold", ticker.change.startsWith('+') ? "text-emerald-400" : "text-red-400")}>
        {ticker.change}
      </div>
    </div>
    <div className="text-lg font-bold text-white mb-4">${ticker.price}</div>
    <div className="absolute bottom-0 left-0 right-0 h-12 opacity-30 group-hover:opacity-50 transition-opacity">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={(sparkline || []).map((v, i) => ({ v, i }))}>
          <Line 
            type="monotone" 
            dataKey="v" 
            stroke={ticker.change.startsWith('+') ? "#00ff88" : "#ff4444"} 
            strokeWidth={2} 
            dot={false} 
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export default function App() {
  const [activeStrategy, setActiveStrategy] = useState("AI Meta-Ensemble");
  const [marketData, setMarketData] = useState(null);
  const [sparkline, setSparkline] = useState([]);
  const [account, setAccount] = useState({});
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [status, setStatus] = useState({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const mData = await api.marketData();
        setMarketData(mData);

        const spark = await api.sparkline();
        if (spark.data) setSparkline(spark.data);

        const acc = await api.account();
        if (!acc.error) setAccount(acc);

        const pos = await api.positions();
        if (pos.positions) setPositions(pos.positions);

        const ord = await api.orders();
        if (ord.orders) setOrders(ord.orders);

        const stat = await api.liveStatus();
        setStatus(stat);
      } catch (e) {
        console.error("Fetch error:", e);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // Update every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen w-full bg-[#0b0e14] text-gray-200 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 flex flex-col p-6 shrink-0">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center">
            <Zap className="text-white fill-current" size={24} />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Quant<span className="text-emerald-500">OS</span></h1>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto no-scrollbar">
          <SidebarItem icon={LayoutDashboard} label="Home" active />
          <SidebarItem icon={Briefcase} label="Strategies" />
          <SidebarItem icon={History} label="Backtests" />
          <SidebarItem icon={Wallet} label="Portfolio" />
          <div className="h-px bg-gray-800 my-6 mx-2" />
          
          <div className="px-4 mb-4">
            <h4 className="text-[10px] uppercase text-gray-500 font-bold tracking-widest mb-4">Intelligence</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 flex items-center gap-2"><BrainCircuit size={14}/> ML Filter</span>
                <div className={cn("w-8 h-4 rounded-full relative cursor-pointer", status.is_running ? "bg-emerald-500" : "bg-gray-700")}>
                  <div className={cn("absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all", status.is_running ? "right-0.5" : "left-0.5")} />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-[10px]">
                  <span className="text-gray-500 uppercase">Confidence</span>
                  <span className="text-emerald-400">75%</span>
                </div>
                <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full w-3/4 bg-emerald-500 rounded-full" />
                </div>
              </div>
            </div>
          </div>

          <div className="px-4 mt-6">
            <h4 className="text-[10px] uppercase text-gray-500 font-bold tracking-widest mb-4">System Status</h4>
            <div className={cn("border rounded-lg p-3 flex items-center gap-3", status.is_running ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20")}>
              <div className={cn("w-2 h-2 rounded-full animate-pulse", status.is_running ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]")} />
              <span className={cn("text-[10px] font-bold uppercase tracking-wider", status.is_running ? "text-emerald-400" : "text-red-400")}>
                {status.is_running ? "Live Execution: Active" : "System: Standby"}
              </span>
            </div>
          </div>
        </nav>

        <div className="pt-6 border-t border-gray-800 space-y-2">
          <SidebarItem icon={HelpCircle} label="Help Center" />
          <SidebarItem icon={LogOut} label="Log Out" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-20 border-b border-gray-800 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-white">Institutional Workstation</h2>
            <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg text-xs">
              <span className="text-gray-500">Mode:</span>
              <span className="text-white font-medium capitalize">{status.mode || 'Offline'}</span>
              <ShieldCheck size={14} className={status.dry_run ? "text-orange-400" : "text-emerald-400"} title={status.dry_run ? "Dry Run" : "Live Trading"} />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-hover:text-emerald-400 transition-colors" size={18} />
              <input 
                type="text" 
                placeholder="Search assets, strategies..." 
                className="bg-[#161a23] border border-gray-800 rounded-xl py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-emerald-500 w-64 transition-all"
              />
            </div>
            <div className="relative cursor-pointer hover:text-white transition-colors">
              <Bell size={20} className="text-gray-400" />
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full border-2 border-[#0b0e14]" />
            </div>
            <div className="flex items-center gap-3 border-l border-gray-800 pl-6 cursor-pointer group">
              <div className="text-right">
                <p className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">Quant Trader</p>
                <p className="text-[10px] text-gray-500 font-medium">Session Active</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-500 to-cyan-500 border-2 border-gray-800" />
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-8 no-scrollbar space-y-8">
          {/* Performance Overview Bar */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
            <MetricCard label="Net Liquidation" value={`$${parseFloat(account.NetLiquidation || 0).toLocaleString()}`} delta="Account Equity" />
            <MetricCard label="Buying Power" value={`$${parseFloat(account.BuyingPower || 0).toLocaleString()}`} delta="Available" />
            <MetricCard label="Daily PnL" value={`$${status.daily_pnl || 0}`} delta={status.daily_pnl >= 0 ? "+$0" : "-$0"} isPositive={status.daily_pnl >= 0} />
            <MetricCard label="Margin Req" value={`$${parseFloat(account.InitMarginReq || 0).toLocaleString()}`} delta="Initial" isPositive={false} />
            <MetricCard label="Excess Liq" value={`$${parseFloat(account.ExcessLiquidity || 0).toLocaleString()}`} delta="Safety Buffer" />
          </div>

          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-12 lg:col-span-8 space-y-8">
              {/* Live Positions Table */}
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-gray-800 flex justify-between items-center">
                  <h3 className="text-md font-bold text-white">Live IBKR Positions</h3>
                  <div className="flex gap-2">
                    <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded border border-emerald-500/20">{positions.length} Active</span>
                  </div>
                </div>
                <div className="p-0 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-[10px] uppercase text-gray-500 bg-[#0b0e14]/50">
                      <tr>
                        <th className="px-6 py-4 font-bold">Symbol</th>
                        <th className="px-6 py-4 font-bold">Type</th>
                        <th className="px-6 py-4 font-bold text-right">Size</th>
                        <th className="px-6 py-4 font-bold text-right">Avg Cost</th>
                        <th className="px-6 py-4 font-bold text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {positions.length > 0 ? positions.map((p, i) => (
                        <tr key={i} className="hover:bg-gray-800/30 transition-colors group">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-white">{p.symbol}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-gray-400 text-xs">{p.secType}</td>
                          <td className={cn("px-6 py-4 text-right font-mono", p.position > 0 ? "text-emerald-400" : "text-red-400")}>
                            {p.position}
                          </td>
                          <td className="px-6 py-4 text-right font-mono text-gray-300">${parseFloat(p.avgCost).toFixed(2)}</td>
                          <td className="px-6 py-4 text-right">
                             <button className="text-[10px] text-red-400 font-bold hover:bg-red-500/10 px-2 py-1 rounded border border-red-500/20 opacity-0 group-hover:opacity-100 transition-all">CLOSE</button>
                          </td>
                        </tr>
                      )) : (
                        <tr><td colSpan="5" className="px-6 py-10 text-center text-gray-500 text-xs italic">No active positions detected in IBKR</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Active Orders Table */}
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-gray-800 flex justify-between items-center">
                  <h3 className="text-md font-bold text-white">Order Management</h3>
                  <Activity size={16} className="text-emerald-500" />
                </div>
                <div className="p-0 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-[10px] uppercase text-gray-500 bg-[#0b0e14]/50">
                      <tr>
                        <th className="px-6 py-4 font-bold">Order ID</th>
                        <th className="px-6 py-4 font-bold">Symbol</th>
                        <th className="px-6 py-4 font-bold">Action</th>
                        <th className="px-6 py-4 font-bold text-right">Qty</th>
                        <th className="px-6 py-4 font-bold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {orders.length > 0 ? orders.map((o, i) => (
                        <tr key={i} className="hover:bg-gray-800/30 transition-colors">
                          <td className="px-6 py-4 font-mono text-xs text-gray-500">#{o.orderId}</td>
                          <td className="px-6 py-4 font-bold text-white">{o.symbol}</td>
                          <td className={cn("px-6 py-4 text-xs font-bold", o.action === "BUY" ? "text-emerald-400" : "text-red-400")}>{o.action}</td>
                          <td className="px-6 py-4 text-right font-mono">{o.filled}/{o.totalQuantity}</td>
                          <td className="px-6 py-4">
                            <span className={cn(
                              "text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider",
                              o.status === "Filled" ? "bg-emerald-500/10 text-emerald-400" : "bg-blue-500/10 text-blue-400"
                            )}>
                              {o.status}
                            </span>
                          </td>
                        </tr>
                      )) : (
                        <tr><td colSpan="5" className="px-6 py-10 text-center text-gray-500 text-xs italic">No active orders in the queue</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Sidebar Widgets */}
            <div className="col-span-12 lg:col-span-4 space-y-8">
              {/* Main SPY Ticker */}
              <div className="space-y-4">
                <MiniTicker ticker={{
                  symbol: 'SPY',
                  name: 'S&P 500 ETF Trust',
                  price: marketData?.price || '0.00',
                  change: (marketData?.change >= 0 ? '+' : '') + (marketData?.change_pct || '0.00') + '%'
                }} sparkline={sparkline} />
                
                {/* Other mini tickers (mock) */}
                <div className="grid grid-cols-2 gap-4">
                   <MiniTicker ticker={{ symbol: 'QQQ', name: 'Nasdaq 100', price: '442.10', change: '+2.10%' }} data={[]} />
                   <MiniTicker ticker={{ symbol: 'VIX', name: 'Volatility', price: marketData?.vix || '0.00', change: '-1.4%' }} data={[]} />
                </div>
              </div>

              {/* System Console / Errors */}
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl p-6">
                <h3 className="text-md font-bold text-white mb-6 flex items-center gap-2">
                  <Activity size={18} className="text-emerald-500" /> Live Console
                </h3>
                <div className="space-y-3 max-h-[300px] overflow-y-auto no-scrollbar font-mono text-[10px]">
                  {(status.errors || []).length > 0 ? status.errors.map((err, i) => (
                    <div key={i} className="text-red-400 border-l-2 border-red-500/50 pl-3 py-1 bg-red-500/5">
                      {err}
                    </div>
                  )) : (
                    <div className="text-emerald-400 border-l-2 border-emerald-500/50 pl-3 py-1 bg-emerald-500/5">
                      System operational. No errors detected. Heartbeat: {new Date(status.last_heartbeat).toLocaleTimeString()}
                    </div>
                  )}
                  <div className="text-gray-500 border-l-2 border-gray-700 pl-3 py-1">
                    Orchestrator Uptime: {Math.floor(status.uptime_seconds / 60)}m {Math.floor(status.uptime_seconds % 60)}s
                  </div>
                  <div className="text-gray-500 border-l-2 border-gray-700 pl-3 py-1">
                    Signals Evaluated: {status.signals_evaluated}
                  </div>
                </div>
              </div>

              {/* Market Context */}
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl p-6">
                <h3 className="text-md font-bold text-white mb-6 flex items-center gap-2">
                  <Globe size={18} className="text-emerald-500" /> Market Context
                </h3>
                <div className="space-y-4">
                  {[
                    { label: 'VIX Volatility', value: marketData?.vix || '0.00', status: marketData?.vix > 30 ? 'Hostile' : 'Stable', color: marketData?.vix > 30 ? 'text-red-400' : 'text-emerald-400' },
                    { label: 'RSI (1D)', value: marketData?.rsi || '0.00', status: marketData?.rsi > 70 ? 'Overbought' : (marketData?.rsi < 30 ? 'Oversold' : 'Neutral'), color: 'text-white' },
                    { label: 'SMA 20/50', value: 'Trend', status: (marketData?.price > marketData?.sma_50) ? 'Bullish' : 'Bearish', color: (marketData?.price > marketData?.sma_50) ? 'text-emerald-400' : 'text-red-400' },
                    { label: 'Consec. Losses', value: status.consecutive_losses || '0', status: (status.consecutive_losses >= 2) ? 'Warning' : 'Healthy', color: (status.consecutive_losses >= 2) ? 'text-red-400' : 'text-emerald-400' }
                  ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">{item.label}</p>
                        <p className="text-sm font-bold text-white">{item.value}</p>
                      </div>
                      <div className="text-right">
                        <p className={cn("text-[10px] font-bold uppercase tracking-wider", item.color)}>{item.status}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
