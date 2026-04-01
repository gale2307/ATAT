import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export function createSocket(): Socket {
  if (!socket) {
    socket = io(process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000", {
      transports: ["websocket"],
      autoConnect: true,
    });
  }
  return socket;
}

export function getSocket(): Socket | null {
  return socket;
}
