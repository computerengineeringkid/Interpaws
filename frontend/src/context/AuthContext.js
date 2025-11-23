"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { parseErrorResponse } from "@/utils/api";

// Single Active Session Storage Keys
const AUTH_TOKEN_KEY = "interpaws_auth_token";
const AUTH_USER_KEY = "interpaws_auth_user";
const AUTH_ROLE_KEY = "interpaws_auth_role";

// Role constants for explicit tracking
const ROLES = {
  CLIENT: "client",
  ADMIN: "admin",
};

const AuthContext = createContext(null);

export { AuthContext };

export const AuthProvider = ({ children }) => {
  // Unified state management with separate state variables
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null); // Values: 'client' | 'admin' | null
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Initialize session from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const storedUser = localStorage.getItem(AUTH_USER_KEY);
    const storedRole = localStorage.getItem(AUTH_ROLE_KEY);

    if (storedToken && storedRole) {
      setToken(storedToken);
      setUser(storedUser ? JSON.parse(storedUser) : null);
      setRole(storedRole);
    }

    setLoading(false);
  }, []);

  // Clear all session data - ensures clean state before any new login
  const clearAllSessions = () => {
    // Remove current unified session keys
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem(AUTH_ROLE_KEY);

    // Also remove legacy keys for backward compatibility cleanup
    localStorage.removeItem("interpaws_client_token");
    localStorage.removeItem("interpaws_client_user");
    localStorage.removeItem("interpaws_admin_token");
    localStorage.removeItem("interpaws_admin_user");

    // Reset state
    setToken(null);
    setUser(null);
    setRole(null);
  };

  // Client login - clears any existing session first
  const login = async (email, password) => {
    try {
      // Auto-cleanup: Clear all existing sessions before new login
      clearAllSessions();

      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch("/api/token", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await parseErrorResponse(response);
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();
      const accessToken = data?.access_token;

      const userResponse = await fetch("/api/clients/me", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!userResponse.ok) {
        throw new Error("Failed to fetch user details");
      }

      const userData = await userResponse.json();

      // Store with explicit role tracking
      localStorage.setItem(AUTH_TOKEN_KEY, accessToken);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(userData));
      localStorage.setItem(AUTH_ROLE_KEY, ROLES.CLIENT);

      // Update state
      setToken(accessToken);
      setUser(userData);
      setRole(ROLES.CLIENT);

      return { success: true };
    } catch (error) {
      console.error("Login error:", error);
      return { success: false, error: error.message };
    }
  };

  // Admin login - clears any existing session first
  const adminLogin = async (email, password) => {
    try {
      // Auto-cleanup: Clear all existing sessions before new login
      clearAllSessions();

      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch("/api/staff/login", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await parseErrorResponse(response);
        throw new Error(error.detail || "Admin login failed");
      }

      const data = await response.json();
      const accessToken = data?.access_token;
      const adminData = { email, role: ROLES.ADMIN };

      // Store with explicit role tracking
      localStorage.setItem(AUTH_TOKEN_KEY, accessToken);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(adminData));
      localStorage.setItem(AUTH_ROLE_KEY, ROLES.ADMIN);

      // Update state
      setToken(accessToken);
      setUser(adminData);
      setRole(ROLES.ADMIN);

      return { success: true };
    } catch (error) {
      console.error("Admin login error:", error);
      return { success: false, error: error.message };
    }
  };

  // Register new client - clears any existing session first
  const register = async (name, email, password, clinicId = null) => {
    try {
      // Clear any existing session before registration
      clearAllSessions();

      const response = await fetch("/api/clients", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          email,
          password,
          clinic_id: clinicId,
        }),
      });

      if (!response.ok) {
        const error = await parseErrorResponse(response);
        throw new Error(error.detail || "Registration failed");
      }

      return await login(email, password);
    } catch (error) {
      console.error("Registration error:", error);
      return { success: false, error: error.message };
    }
  };

  // Unified logout - completely purges all authentication data
  const logout = () => {
    clearAllSessions();
    router.push("/login");
  };

  // Memoized context value with unified state
  const value = useMemo(() => {
    return {
      // Primary session state
      token,
      user,
      userRole: role,

      // Authentication status flags
      isAuthenticated: !!token && role === ROLES.CLIENT,
      isAdmin: !!token && role === ROLES.ADMIN,
      isLoggedIn: !!token,

      // Loading state
      loading,

      // Auth actions
      login,
      adminLogin,
      register,
      logout,

      // Legacy compatibility aliases (for Navigation.js and AdminBookingList.js)
      clientToken: role === ROLES.CLIENT ? token : null,
      adminToken: role === ROLES.ADMIN ? token : null,
      clientUser: role === ROLES.CLIENT ? user : null,
      adminUser: role === ROLES.ADMIN ? user : null,
    };
  }, [token, user, role, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
