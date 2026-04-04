import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { superAdminApi } from "@/api/superAdmin";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";
import { KeyRound, Loader2, Shield, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";

export default function AdminManagePage() {
  const { data, loading, error, refetch } = useApi(() => superAdminApi.listAdmins(), []);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; username: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<{ id: string; username: string } | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetting, setResetting] = useState(false);

  async function handleToggleActive(adminId: string) {
    setTogglingId(adminId);
    try {
      const updated = await superAdminApi.toggleActive(adminId);
      toast.success(updated.is_active ? "教师已启用" : "教师已禁用");
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "操作失败");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleResetPassword(e: FormEvent) {
    e.preventDefault();
    if (!resetTarget || !newPassword.trim()) return;
    setResetting(true);
    try {
      await superAdminApi.resetPassword(resetTarget.id, newPassword.trim());
      toast.success("密码已重置");
      setResetTarget(null);
      setNewPassword("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "重置失败");
    } finally {
      setResetting(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await superAdminApi.deleteAdmin(deleteTarget.id);
      toast.success("教师已删除");
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  const admins = data?.items ?? [];

  return (
    <div className="space-y-4 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold page-title-decorated">教师管理</h1>

      {admins.length === 0 ? (
        <EmptyState
          icon={<Shield className="h-12 w-12" />}
          title="暂无教师"
          description="教师可通过邀请码自助注册"
        />
      ) : (
        <>
          <p className="text-sm text-muted-foreground">共 {admins.length} 个教师</p>
          <Table className="data-table">
            <TableHeader>
              <TableRow>
                <TableHead>账号</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>班级数量</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {admins.map((admin) => (
                <TableRow key={admin.id}>
                  <TableCell className="font-medium">{admin.username}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {admin.category ?? "\u2014"}
                  </TableCell>
                  <TableCell>
                    {admin.is_active ? (
                      <Badge variant="default">启用</Badge>
                    ) : (
                      <Badge variant="destructive">已禁用</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {admin.class_count}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(admin.created_at)}
                  </TableCell>
                  <TableCell className="text-right space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={togglingId === admin.id}
                      onClick={() => handleToggleActive(admin.id)}
                      title={admin.is_active ? "禁用" : "启用"}
                    >
                      {togglingId === admin.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : admin.is_active ? (
                        <ToggleRight className="h-4 w-4" />
                      ) : (
                        <ToggleLeft className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setResetTarget({ id: admin.id, username: admin.username })}
                      title="重置密码"
                    >
                      <KeyRound className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteTarget({ id: admin.id, username: admin.username })}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="删除教师"
        description={`确定要删除教师「${deleteTarget?.username}」吗？将级联删除该教师的所有班级和数据，此操作不可撤销。`}
        confirmText="删除"
        onConfirm={handleDelete}
        loading={deleting}
      />

      <Dialog
        open={!!resetTarget}
        onOpenChange={(open) => {
          if (!open) {
            setResetTarget(null);
            setNewPassword("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重置密码 — {resetTarget?.username}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new-password">新密码</Label>
              <Input
                id="new-password"
                type="password"
                placeholder="请输入新密码"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <DialogFooter>
              <DialogClose render={<Button type="button" variant="outline" />}>
                取消
              </DialogClose>
              <Button type="submit" disabled={!newPassword.trim() || resetting}>
                {resetting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                确认重置
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
