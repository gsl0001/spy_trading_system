import React, { useState } from 'react';
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

// Mock Data
const equityData = [
  { time: '09:30', value: 100000 },
  { time: '10:00', value: 101200 },
  { time: '10:30', value: 100800 },
  { time: '11:00', value: 102500 },
  { time: '11:30', value: 103100 },
  { time: '12:00', value: 102900 },
  { time: '12:30', value: 104500 },
  { time: '13:00', value: 105800 },
  { time: '13:30', value: 105200 },
  { time: '14:00', value: 106900 },
  { time: '14:30', value: 108200 },
  { time: '15:00', value: 107500 },
  { time: '15:30', value: 109000 },
  { time: '16:00', value: 110450 },
];

const priceData = [
  { time: '10:00', open: 512.4, high: 513.8, low: 511.9, close: 513.2, volume: 1200000 },
  { time: '11:00', open: 513.2, high: 515.1, low: 512.8, close: 514.7, volume: 1500000 },
  { time: '12:00', open: 514.7, high: 514.9, low: 513.5, close: 513.8, volume: 900000 },
  { time: '13:00', open: 513.8, high: 516.4, low: 513.2, close: 515.9, volume: 2100000 },
  { time: '14:00', open: 515.9, high: 517.8, low: 515.5, close: 517.2, volume: 1800000 },
  { time: '15:00', open: 517.2, high: 518.5, low: 516.8, close: 518.1, volume: 2500000 },
];

const strategyRankings = [
  { name: 'Strategy 36: AI Meta-Ensemble', return: '+24.5%', winRate: '68%', sharpe: '2.8' },
  { name: 'Strategy 11: Combo Alpha', return: '+18.2%', winRate: '62%', sharpe: '2.1' },
  { name: 'Strategy 10: Insider Alpha', return: '+15.9%', winRate: '58%', sharpe: '1.9' },
  { name: 'Strategy 1: 20/50 Pullback', return: '+12.4%', winRate: '55%', sharpe: '1.5' },
  { name: 'Strategy 3: Mean Reversion', return: '+9.8%', winRate: '52%', sharpe: '1.2' },
];

const tickers = [
  { symbol: 'SPY', name: 'S&P 500 ETF', price: '518.24', change: '+1.45%', data: [10, 15, 12, 18, 25, 22, 30] },
  { symbol: 'QQQ', name: 'Nasdaq 100 ETF', price: '442.10', change: '+2.10%', data: [5, 12, 18, 15, 22, 28, 35] },
  { symbol: 'DIA', name: 'Dow Jones ETF', price: '389.50', change: '+0.85%', data: [20, 18, 22, 20, 25, 24, 28] },
  { symbol: 'IWM', name: 'Russell 2000 ETF', price: '204.30', change: '-0.32%', data: [30, 25, 28, 22, 20, 18, 15] },
];

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

const MiniTicker = ({ ticker }) => (
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
        <LineChart data={ticker.data.map((v, i) => ({ v, i }))}>
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

  return (
    <div className="flex h-screen w-full bg-[#0b0e14] text-gray-200 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 flex flex-col p-6 shrink-0">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center">
            <Zap className="text-white fill-current" size={24} />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">FinX <span className="text-emerald-500">Quant</span></h1>
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
                <div className="w-8 h-4 bg-emerald-500 rounded-full relative cursor-pointer">
                  <div className="absolute right-0.5 top-0.5 w-3 h-3 bg-white rounded-full" />
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
            <h4 className="text-[10px] uppercase text-gray-500 font-bold tracking-widest mb-4">Market Status</h4>
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3 flex items-center gap-3">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Market Open: LIVE</span>
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
            <h2 className="text-xl font-bold text-white">Workstation Dashboard</h2>
            <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg text-xs">
              <span className="text-gray-500">Interval:</span>
              <span className="text-white font-medium">15m</span>
              <ChevronDown size={14} className="text-gray-500" />
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
                <p className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">John Doe</p>
                <p className="text-[10px] text-gray-500 font-medium">Pro Trader</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-500 to-cyan-500 border-2 border-gray-800" />
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-8 no-scrollbar space-y-8">
          {/* Performance Overview Bar */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
            <MetricCard label="Total Equity" value="$110,450.22" delta="+10.45%" />
            <MetricCard label="Profit Factor" value="2.84" delta="Excellent" />
            <MetricCard label="Win Rate" value="68.2%" delta="+2.1%" />
            <MetricCard label="Max Drawdown" value="4.12%" delta="Safe" isPositive={true} />
            <MetricCard label="Sharpe Ratio" value="3.15" delta="Top 1%" />
          </div>

          <div className="grid grid-cols-12 gap-8">
            {/* Main Equity Chart */}
            <div className="col-span-12 lg:col-span-8 space-y-8">
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h3 className="text-lg font-bold text-white mb-1">Equity Performance Curve</h3>
                    <p className="text-xs text-gray-500">Live account synchronization active</p>
                  </div>
                  <div className="flex bg-[#0b0e14] p-1 rounded-lg border border-gray-800">
                    {['1D', '1W', '1M', '3M', '1Y'].map((t) => (
                      <button 
                        key={t} 
                        className={cn(
                          "px-3 py-1.5 rounded-md text-[10px] font-bold transition-all",
                          t === '1D' ? "bg-emerald-500 text-white shadow-lg" : "text-gray-500 hover:text-white"
                        )}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityData}>
                      <defs>
                        <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00ff88" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#00ff88" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#22262e" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#4b5563" 
                        fontSize={10} 
                        tickLine={false} 
                        axisLine={false} 
                        dy={10}
                      />
                      <YAxis 
                        stroke="#4b5563" 
                        fontSize={10} 
                        tickLine={false} 
                        axisLine={false} 
                        tickFormatter={(v) => `$${v/1000}k`}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#161a23', border: '1px solid #374151', borderRadius: '12px' }}
                        itemStyle={{ color: '#00ff88' }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#00ff88" 
                        strokeWidth={3} 
                        fillOpacity={1} 
                        fill="url(#colorValue)" 
                        animationDuration={2000}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Secondary Chart: Price / Volume */}
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center border border-white/10">
                      <img src="https://img.icons8.com/color/48/us-dollar-exchange.png" className="w-8 h-8" alt="SPY" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        SPY <span className="text-xs font-normal text-gray-500 tracking-normal">S&P 500 ETF Trust</span>
                      </h3>
                      <p className="text-2xl font-mono text-white">$518.24 <span className="text-sm text-emerald-400 ml-2">+1.45%</span></p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button className="p-2 bg-gray-900 border border-gray-800 rounded-lg hover:border-emerald-500 transition-colors">
                      <Settings size={18} className="text-gray-400" />
                    </button>
                    <button className="p-2 bg-gray-900 border border-gray-800 rounded-lg hover:border-emerald-500 transition-colors">
                      <Filter size={18} className="text-gray-400" />
                    </button>
                  </div>
                </div>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={priceData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#22262e" />
                      <XAxis dataKey="time" stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} />
                      <YAxis stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#161a23', border: '1px solid #374151', borderRadius: '12px' }}
                      />
                      <Bar dataKey="volume" yAxisId={0} fill="#374151" opacity={0.3} barSize={40} />
                      <Line 
                        type="monotone" 
                        dataKey="close" 
                        stroke="#00ff88" 
                        strokeWidth={2} 
                        dot={{ r: 4, fill: '#00ff88', strokeWidth: 0 }} 
                        activeDot={{ r: 6, stroke: '#161a23', strokeWidth: 2 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Sidebar Widgets */}
            <div className="col-span-12 lg:col-span-4 space-y-8">
              {/* Tickers */}
              <div className="grid grid-cols-2 gap-4">
                {tickers.map((t) => <MiniTicker key={t.symbol} ticker={t} />)}
              </div>

              {/* Strategy Rankings */}
              <div className="bg-[#161a23] border border-gray-800 rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-gray-800 flex justify-between items-center">
                  <h3 className="text-md font-bold text-white">Strategy Alpha Rankings</h3>
                  <button className="text-[10px] text-emerald-400 font-bold hover:underline">VIEW ALL</button>
                </div>
                <div className="p-4">
                  <div className="space-y-4">
                    {strategyRankings.map((s, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-800/50 transition-colors group cursor-pointer border border-transparent hover:border-gray-700">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold",
                            i === 0 ? "bg-emerald-500/20 text-emerald-400" : "bg-gray-800 text-gray-500"
                          )}>
                            {i + 1}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">{s.name}</p>
                            <p className="text-[10px] text-gray-500">Sharpe: {s.sharpe} • Win Rate: {s.winRate}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold text-emerald-400 font-mono">{s.return}</p>
                          <TrendingUp size={12} className="text-emerald-500 ml-auto" />
                        </div>
                      </div>
                    ))}
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
                    { label: 'VIX Volatility', value: '14.22', status: 'Stable', color: 'text-emerald-400' },
                    { label: '10Y Treasury', value: '4.25%', status: 'Rising', color: 'text-red-400' },
                    { label: 'Insider Bias', value: '1.24', status: 'Accumulating', color: 'text-emerald-400' },
                    { label: 'AI Sentiment', value: '78/100', status: 'Bullish', color: 'text-emerald-400' }
                  ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">{item.label}</p>
                        <p className="text-sm font-bold text-white">{item.value}</p>
                      </div>
                      <div className="text-right">
                        <p className={cn("text-[10px] font-bold uppercase tracking-wider", item.color)}>{item.status}</p>
                        <div className="flex gap-1 mt-1">
                          {[1,2,3,4,5].map(b => (
                            <div key={b} className={cn("w-1.5 h-1.5 rounded-full", b <= (4-i) ? "bg-emerald-500" : "bg-gray-800")} />
                          ))}
                        </div>
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
