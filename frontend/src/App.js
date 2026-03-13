import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';

import Login from './components/auth/Login';
import Layout from './components/common/Layout';
import Dashboard from './components/dashboard/Dashboard';
import SeriesList from './components/series/SeriesList';
import SeriesDetail from './components/series/SeriesDetail';
import BaseDetail from './components/bases/BaseDetail';
import PantoneTargets from './components/pantone/PantoneTargets';
import PantoneFormulas from './components/pantone/PantoneFormulas';
import PantoneFormulate from './components/pantone/PantoneFormulate';
import FormulaDetail from './components/pantone/FormulaDetail';
import CustomMatchNew from './components/custom/CustomMatchNew';
import CustomMatchList from './components/custom/CustomMatchList';
import CustomMatchDetail from './components/custom/CustomMatchDetail';
import SubstrateList from './components/substrates/SubstrateList';
import UserManagement from './components/admin/UserManagement';
import AuditLog from './components/admin/AuditLog';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    if (stored && token) {
      setUser(JSON.parse(stored));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, token) => {
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', token);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <ToastContainer position="top-right" autoClose={3000} />
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/" /> : <Login onLogin={handleLogin} />}
        />
        {user ? (
          <Route element={<Layout user={user} onLogout={handleLogout} />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/series" element={<SeriesList />} />
            <Route path="/series/:id" element={<SeriesDetail />} />
            <Route path="/bases/:id" element={<BaseDetail />} />
            <Route path="/substrates" element={<SubstrateList />} />
            <Route path="/pantone/targets" element={<PantoneTargets />} />
            <Route path="/pantone/formulas" element={<PantoneFormulas />} />
            <Route path="/pantone/formulate" element={<PantoneFormulate />} />
            <Route path="/pantone/formulas/:id" element={<FormulaDetail />} />
            <Route path="/custom-match/new" element={<CustomMatchNew />} />
            <Route path="/custom-match" element={<CustomMatchList />} />
            <Route path="/custom-match/:id" element={<CustomMatchDetail />} />
            <Route path="/admin/users" element={<UserManagement />} />
            <Route path="/admin/audit-log" element={<AuditLog />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Route>
        ) : (
          <Route path="*" element={<Navigate to="/login" />} />
        )}
      </Routes>
    </Router>
  );
}

export default App;
