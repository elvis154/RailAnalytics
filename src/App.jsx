import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import Home from './Home.jsx';
import About from './About.jsx';
import Dashboard from './Dashboard.jsx';
import Login from './Auth/Login.jsx';
import Signup from './Auth/Signin.jsx';
import PrivateRoute from './components/PrivateRoute.jsx';
import Display from './components/Display';
import Insert from './components/Insert';
import Edit from './components/Edit';
import Use from './components/Use';

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/about" element={<PrivateRoute><About /></PrivateRoute>} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>}>
          <Route index element={<Display />} />
          <Route path="display" element={<Display />} />
          <Route path="insert" element={<Insert />} />
          <Route path="edit" element={<Edit />} />
          <Route path="use" element={<Use />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}

export default App; 