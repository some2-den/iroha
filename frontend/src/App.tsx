import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import Dashboard from './pages/Dashboard';
import StaffPerformance from './pages/StaffPerformance';
import AdminPanel from './pages/AdminPanel';
import { DailySalesChart, ProductSalesChart } from './components/Charts';
import { getDailySummary, getProductSummary } from './api';

interface DailySummaryData {
  date: string;
  store_code: string;
  total_sales: number;
  gross_profit: number;
  transaction_count: number;
}

interface ProductSummaryData {
  product_name: string;
  total_sales: number;
  total_gross_profit: number;
  total_quantity: number;
}

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'upload' | 'analysis' | 'staff' | 'admin'>('dashboard');
  const [dailyData, setDailyData] = useState<DailySummaryData[]>([]);
  const [productData, setProductData] = useState<ProductSummaryData[]>([]);

  const handleUploadSuccess = () => {
    // アップロード成功時にデータを再取得
    setActiveTab('dashboard');
  };

  const handleAnalyze = async () => {
    try {
      const [dailyRes, productRes] = await Promise.all([
        getDailySummary(),
        getProductSummary(),
      ]);
      setDailyData(dailyRes.data);
      setProductData(productRes.data);
      setActiveTab('analysis');
    } catch (error) {
      console.error('Error fetching analysis data:', error);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5', fontFamily: 'sans-serif' }}>
      <header style={{ backgroundColor: '#2c3e50', color: 'white', padding: '20px' }}>
        <h1>📊 売上実績管理</h1>
        <p>CSVアップロード・分析ダッシュボード</p>
      </header>

      <nav style={{ backgroundColor: '#34495e', padding: '0' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setActiveTab('dashboard')}
            style={{
              padding: '12px 20px',
              backgroundColor: activeTab === 'dashboard' ? '#3498db' : '#34495e',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            ダッシュボード
          </button>
          <button
            onClick={() => setActiveTab('staff')}
            style={{
              padding: '12px 20px',
              backgroundColor: activeTab === 'staff' ? '#3498db' : '#34495e',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            個人別実績
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            style={{
              padding: '12px 20px',
              backgroundColor: activeTab === 'upload' ? '#3498db' : '#34495e',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            ファイルアップロード
          </button>
          <button
            onClick={handleAnalyze}
            style={{
              padding: '12px 20px',
              backgroundColor: activeTab === 'analysis' ? '#3498db' : '#34495e',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            分析・グラフ
          </button>
          <button
            onClick={() => setActiveTab('admin')}
            style={{
              padding: '12px 20px',
              backgroundColor: activeTab === 'admin' ? '#e74c3c' : '#34495e',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            管理者ページ
          </button>
        </div>
      </nav>

      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'staff' && <StaffPerformance />}
        {activeTab === 'upload' && <FileUpload onUploadSuccess={handleUploadSuccess} />}
        {activeTab === 'analysis' && (
          <div>
            <DailySalesChart data={dailyData} />
            <ProductSalesChart data={productData} />
          </div>
        )}
        {activeTab === 'admin' && <AdminPanel />}
      </main>
    </div>
  );
}

export default App;
