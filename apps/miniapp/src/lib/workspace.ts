import type { Workspace } from "../types";

export function getWorkspaceMembership(workspace: Workspace, userId: number) {
  return workspace.members.find((member) => member.user.id === userId) ?? null;
}

export function isWorkspaceAdmin(workspace: Workspace, userId: number) {
  const membership = getWorkspaceMembership(workspace, userId);
  return membership?.role === "owner" || membership?.role === "admin";
}

export function parseWorkspaceId(value: string | null) {
  if (!value) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
