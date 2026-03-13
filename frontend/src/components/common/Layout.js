import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Nav, Dropdown } from 'react-bootstrap';

function Layout({ user, onLogout }) {
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const canFormulate = user?.role === 'admin' || user?.role === 'formulator';

  return (
    <div className="d-flex">
      <div className="sidebar">
        <div className="brand">
          Color Formulation
          <small>Ink Management System</small>
        </div>

        <Nav className="flex-column flex-grow-1">
          <NavLink to="/" className="nav-link" end>Dashboard</NavLink>

          <div className="section-label">Ink Management</div>
          <NavLink to="/series" className="nav-link">Ink Series</NavLink>
          <NavLink to="/substrates" className="nav-link">Substrates</NavLink>

          <div className="section-label">Pantone</div>
          <NavLink to="/pantone/targets" className="nav-link">Color Targets</NavLink>
          <NavLink to="/pantone/formulas" className="nav-link">Formulas</NavLink>
          {canFormulate && (
            <NavLink to="/pantone/formulate" className="nav-link">Generate Formula</NavLink>
          )}

          <div className="section-label">Custom Match</div>
          <NavLink to="/custom-match" className="nav-link">Match History</NavLink>
          {canFormulate && (
            <NavLink to="/custom-match/new" className="nav-link">New Match</NavLink>
          )}

          {(isAdmin || canFormulate) && (
            <>
              <div className="section-label">Settings</div>
              <NavLink to="/admin/tolerance-profiles" className="nav-link">Tolerance Profiles</NavLink>
            </>
          )}

          {isAdmin && (
            <>
              <div className="section-label">Administration</div>
              <NavLink to="/admin/users" className="nav-link">User Management</NavLink>
              <NavLink to="/admin/audit-log" className="nav-link">Audit Log</NavLink>
            </>
          )}
        </Nav>

        <div className="sidebar-user">
          <Dropdown>
            <Dropdown.Toggle variant="link" className="dropdown-toggle">
              <span className="user-name">{user?.full_name || user?.username}</span>
              <br />
              <span className="user-role">{user?.role}</span>
            </Dropdown.Toggle>
            <Dropdown.Menu>
              <Dropdown.Item onClick={() => {
                onLogout();
                navigate('/login');
              }}>
                Sign Out
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      </div>

      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
}

export default Layout;
