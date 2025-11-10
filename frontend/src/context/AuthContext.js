"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [userRole, setUserRole] = useState(null); // 'client' or 'admin'
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check for existing token in localStorage
    const storedToken = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");
    const storedRole = localStorage.getItem("userRole");

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      setUserRole(storedRole);
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      // Create FormData for OAuth2PasswordRequestForm
      const formData = new FormData();
      formData.append("username", email); // OAuth2 uses 'username' field
      formData.append("password", password);

      const response = await fetch("http://localhost:8000/token", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();
      const accessToken = data.access_token;

      // Get user details
      const userResponse = await fetch("http://localhost:8000/clients/me", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!userResponse.ok) {
        throw new Error("Failed to fetch user details");
      }

      const userData = await userResponse.json();

      // Store token, user data, and role
      localStorage.setItem("token", accessToken);
      localStorage.setItem("user", JSON.stringify(userData));
      localStorage.setItem("userRole", "client");
      setToken(accessToken);
      setUser(userData);
      setUserRole("client");

      return { success: true };
    } catch (error) {
      console.error("Login error:", error);
      return { success: false, error: error.message };
    }
  };

  const adminLogin = async (email, password) => {
    try {
      // Create FormData for OAuth2PasswordRequestForm
      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch("http://localhost:8000/staff/login", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Admin login failed");
      }

      const data = await response.json();
      const accessToken = data.access_token;

      // For admin, we store the token but don't have a /staff/me endpoint
      // We'll just store basic info from the token
      const adminData = { email, role: "admin" };

      // Store token, admin data, and role
      localStorage.setItem("token", accessToken);
      localStorage.setItem("user", JSON.stringify(adminData));
      localStorage.setItem("userRole", "admin");
      setToken(accessToken);
      setUser(adminData);
      setUserRole("admin");

      return { success: true };
    } catch (error) {
      console.error("Admin login error:", error);
      return { success: false, error: error.message };
    }
  };

  const register = async (name, email, password, clinicId = null) => {
    try {
      const response = await fetch("http://localhost:8000/clients/", {
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
        const error = await response.json();
        throw new Error(error.detail || "Registration failed");
      }

      // Auto-login after registration
      return await login(email, password);
    } catch (error) {
      console.error("Registration error:", error);
      return { success: false, error: error.message };
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("userRole");
    setToken(null);
    setUser(null);
    setUserRole(null);
    router.push("/login");
  };

  const value = {
    user,
    token,
    userRole,
    loading,
    login,
    adminLogin,
    register,
    logout,
    isAuthenticated: !!token && userRole === "client",
    isAdmin: !!token && userRole === "admin",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
