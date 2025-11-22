"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const CLIENT_TOKEN_KEY = "interpaws_client_token";
const CLIENT_USER_KEY = "interpaws_client_user";
const ADMIN_TOKEN_KEY = "interpaws_admin_token";
const ADMIN_USER_KEY = "interpaws_admin_user";

const AuthContext = createContext(null);

export { AuthContext };

export const AuthProvider = ({ children }) => {
  const [clientSession, setClientSession] = useState({ token: null, user: null });
  const [adminSession, setAdminSession] = useState({ token: null, user: null });
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const storedClientToken = localStorage.getItem(CLIENT_TOKEN_KEY);
    const storedClientUser = localStorage.getItem(CLIENT_USER_KEY);
    const storedAdminToken = localStorage.getItem(ADMIN_TOKEN_KEY);
    const storedAdminUser = localStorage.getItem(ADMIN_USER_KEY);

    setClientSession({
      token: storedClientToken || null,
      user: storedClientUser ? JSON.parse(storedClientUser) : null,
    });

    setAdminSession({
      token: storedAdminToken || null,
      user: storedAdminUser ? JSON.parse(storedAdminUser) : null,
    });

    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch("/api/token", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
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

      localStorage.setItem(CLIENT_TOKEN_KEY, accessToken);
      localStorage.setItem(CLIENT_USER_KEY, JSON.stringify(userData));
      setClientSession({ token: accessToken, user: userData });

      return { success: true };
    } catch (error) {
      console.error("Login error:", error);
      return { success: false, error: error.message };
    }
  };

  const adminLogin = async (email, password) => {
    try {
      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch("/api/staff/login", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Admin login failed");
      }

      const data = await response.json();
      const accessToken = data?.access_token;
      const adminData = { email, role: "admin" };

      localStorage.setItem(ADMIN_TOKEN_KEY, accessToken);
      localStorage.setItem(ADMIN_USER_KEY, JSON.stringify(adminData));
      setAdminSession({ token: accessToken, user: adminData });

      return { success: true };
    } catch (error) {
      console.error("Admin login error:", error);
      return { success: false, error: error.message };
    }
  };

  const register = async (name, email, password, clinicId = null) => {
    try {
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
        const error = await response.json();
        throw new Error(error.detail || "Registration failed");
      }

      return await login(email, password);
    } catch (error) {
      console.error("Registration error:", error);
      return { success: false, error: error.message };
    }
  };

  const logoutClient = () => {
    localStorage.removeItem(CLIENT_TOKEN_KEY);
    localStorage.removeItem(CLIENT_USER_KEY);
    setClientSession({ token: null, user: null });
  };

  const logoutAdmin = () => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_USER_KEY);
    setAdminSession({ token: null, user: null });
  };

  const logout = () => {
    logoutClient();
    logoutAdmin();
    router.push("/login");
  };

  const value = useMemo(() => {
    const clientToken = clientSession.token;
    const adminToken = adminSession.token;
    return {
      clientToken,
      clientUser: clientSession.user,
      adminToken,
      adminUser: adminSession.user,
      loading,
      login,
      adminLogin,
      register,
      logout,
      logoutAdmin,
      logoutClient,
      isAuthenticated: !!clientToken,
      isAdmin: !!adminToken,
      token: clientToken,
      user: clientSession.user,
      userRole: clientToken ? "client" : adminToken ? "admin" : null,
    };
  }, [clientSession, adminSession, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
