import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import axios from "axios";

export default NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        try {
          const res = await axios.post(
            "http://127.0.0.1:8000/api/auth/login",
            {
              email: credentials.email,
              password: credentials.password
            },
            { headers: { "Content-Type": "application/json" } }
          );
          const user = res.data.user;
          if (user) {
            user.accessToken = res.data.access_token;
            user.refreshToken = res.data.refresh_token;
            return user;
          }
          return null;
        } catch (err) {
          return null;
        }
      }
    })
  ],
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // 7 days
  },
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        token.role = user.role;
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
      }

      // Check if token needs refresh
      if (token.accessToken) {
        const tokenExp = JSON.parse(atob(token.accessToken.split('.')[1])).exp * 1000;
        if (Date.now() >= tokenExp - 5 * 60 * 1000) { // Refresh 5 minutes before expiry
          try {
            const res = await axios.post(
              "http://127.0.0.1:8000/api/auth/refresh",
              { refresh_token: token.refreshToken },
              { headers: { "Content-Type": "application/json" } }
            );
            token.accessToken = res.data.access_token;
            token.refreshToken = res.data.refresh_token;
          } catch (error) {
            return { ...token, error: "RefreshAccessTokenError" };
          }
        }
      }

      return token;
    },
    async session({ session, token }) {
      session.user.id = token.id;
      session.user.email = token.email;
      session.user.name = token.name;
      session.user.role = token.role;
      session.accessToken = token.accessToken;
      session.error = token.error;
      return session;
    }
  },
  pages: {
    signIn: "/login",
    error: "/login"
  }
}); 