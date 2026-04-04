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
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { inviteCodeApi, type InviteCodeCreateResponse } from "@/api/inviteCodes";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";
import { Check, Copy, Loader2, Plus, RefreshCw, Ticket, Trash2 } from "lucide-react";

export default function InviteCodeManagePage() {
  const { data, loading, error, refetch } = useApi(() => inviteCodeApi.list(), []);

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [category, setCategory] = useState("");
  const [creating, setCreating] = useState(false);

  // Code result dialog (shown after create or regenerate)
  const [codeResult, setCodeResult] = useState<InviteCodeCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Delete
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; category: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Regenerate
  const [regenerateTarget, setRegenerateTarget] = useState<{ id: string; category: string } | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!category.trim()) return;
    setCreating(true);
    try {
      const result = await inviteCodeApi.create(category.trim());
      setCreateOpen(false);
      setCategory("");
      setCodeResult(result);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await inviteCodeApi.delete(deleteTarget.id);
      toast.success("邀请码已删除");
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  async function handleRegenerate() {
    if (!regenerateTarget) return;
    setRegenerating(true);
    try {
      const result = await inviteCodeApi.regenerate(regenerateTarget.id);
      setRegenerateTarget(null);
      setCodeResult(result);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "重新生成失败");
    } finally {
      setRegenerating(false);
    }
  }

  async function handleCopy(code: string) {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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

  const codes = data?.items ?? [];

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold page-title-decorated">邀请码管理</h1>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger render={<Button />}>
            <Plus className="mr-2 h-4 w-4" />
            创建邀请码
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建邀请码</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="invite-category">分类名称</Label>
                <Input
                  id="invite-category"
                  placeholder="如：物理学院、计算机系"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </div>
              <DialogFooter>
                <DialogClose render={<Button type="button" variant="outline" />}>
                  取消
                </DialogClose>
                <Button type="submit" disabled={!category.trim() || creating}>
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  创建
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {codes.length === 0 ? (
        <EmptyState
          icon={<Ticket className="h-12 w-12" />}
          title="暂无邀请码"
          description="创建邀请码后，教师可凭邀请码自助注册"
        />
      ) : (
        <>
          <p className="text-sm text-muted-foreground">共 {codes.length} 个邀请码</p>
          <Table className="data-table">
            <TableHeader>
              <TableRow>
                <TableHead>分类名称</TableHead>
                <TableHead>已注册人数</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {codes.map((code) => (
                <TableRow key={code.id}>
                  <TableCell className="font-medium">{code.category}</TableCell>
                  <TableCell className="text-muted-foreground">{code.registered_count}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(code.created_at)}</TableCell>
                  <TableCell className="text-right space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setRegenerateTarget({ id: code.id, category: code.category })}
                      title="重新生成"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteTarget({ id: code.id, category: code.category })}
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

      {/* Delete confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="删除邀请码"
        description={`确定要删除「${deleteTarget?.category}」的邀请码吗？已注册教师不受影响，但新教师将无法使用此码注册。`}
        confirmText="删除"
        onConfirm={handleDelete}
        loading={deleting}
      />

      {/* Regenerate confirmation */}
      <ConfirmDialog
        open={!!regenerateTarget}
        onOpenChange={(open) => !open && setRegenerateTarget(null)}
        title="重新生成邀请码"
        description={`确定要重新生成「${regenerateTarget?.category}」的邀请码吗？旧邀请码将立即失效。`}
        confirmText="重新生成"
        variant="default"
        onConfirm={handleRegenerate}
        loading={regenerating}
      />

      {/* Code result dialog */}
      <Dialog
        open={!!codeResult}
        onOpenChange={(open) => {
          if (!open) {
            setCodeResult(null);
            setCopied(false);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>邀请码已生成</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              分类：{codeResult?.category}
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-md bg-muted px-3 py-2 text-sm font-mono select-all">
                {codeResult?.code}
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => codeResult && handleCopy(codeResult.code)}
              >
                {copied ? (
                  <Check className="h-4 w-4 text-success" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              请妥善保存此邀请码，关闭后将无法再次查看。
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => { setCodeResult(null); setCopied(false); }}>
              确定
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
