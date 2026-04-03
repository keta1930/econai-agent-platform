import { useState, type FormEvent } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { superAdminApi } from "@/api/superAdmin";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";
import { Loader2, Plus, Shield } from "lucide-react";

export default function AdminManagePage() {
  const { data, loading, error, refetch } = useApi(() => superAdminApi.listAdmins(), []);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [creating, setCreating] = useState(false);

  const isFormValid = username.trim() && password.trim();

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!isFormValid) return;
    setCreating(true);
    try {
      await superAdminApi.createAdmin({
        username: username.trim(),
        password: password.trim(),
      });
      toast.success("管理员已创建");
      setDialogOpen(false);
      setUsername("");
      setPassword("");
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-28" />
        </div>
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold page-title-decorated">管理员管理</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>
            <Plus className="mr-2 h-4 w-4" />
            创建管理员
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建管理员</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="admin-username">账号</Label>
                <Input
                  id="admin-username"
                  placeholder="请输入管理员账号"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-password">密码</Label>
                <Input
                  id="admin-password"
                  type="password"
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <DialogFooter>
                <DialogClose render={<Button type="button" variant="outline" />}>
                  取消
                </DialogClose>
                <Button type="submit" disabled={!isFormValid || creating}>
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  创建
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {admins.length === 0 ? (
        <EmptyState
          icon={<Shield className="h-12 w-12" />}
          title="暂无管理员"
          description="创建第一个管理员账号"
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">管理员列表 ({admins.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>账号</TableHead>
                    <TableHead>班级数量</TableHead>
                    <TableHead>创建时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {admins.map((admin) => (
                    <TableRow key={admin.id}>
                      <TableCell className="font-medium">{admin.username}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {admin.class_count}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(admin.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
