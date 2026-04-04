import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { useClassContext } from "@/contexts/ClassContext";
import { rosterApi } from "@/api/roster";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";
import {
  Loader2,
  Plus,
  Upload,
  Trash2,
  Users,
  KeyRound,
  UserMinus,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ActualRosterItem } from "@/types/roster";

type RosterTab = "expected" | "actual";

const COLLEGE_LABELS: Record<string, string> = {
  lingnan: "岭南学院",
  physics: "物理学院",
};

export default function RosterPage() {
  const { classes } = useClassContext();
  const [selectedClassId, setSelectedClassId] = useState<string | null>(null);
  const selectedClass = classes.find((c) => c.id === selectedClassId) ?? null;
  const [activeTab, setActiveTab] = useState<RosterTab>("expected");

  const { data, loading, error, refetch } = useApi(
    () =>
      selectedClassId
        ? rosterApi.list(selectedClassId)
        : Promise.resolve({ expected: [], actual: [] }),
    [selectedClassId],
  );

  // Single add
  const [newId, setNewId] = useState("");
  const [adding, setAdding] = useState(false);

  // Batch import
  const [batchText, setBatchText] = useState("");
  const [batchOpen, setBatchOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [batchResult, setBatchResult] = useState<{
    added: number;
    duplicates: number;
  } | null>(null);

  // Delete single expected
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Reset password
  const [resetTarget, setResetTarget] = useState<ActualRosterItem | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetting, setResetting] = useState(false);

  // Remove single member
  const [removeTarget, setRemoveTarget] = useState<ActualRosterItem | null>(
    null,
  );
  const [removing, setRemoving] = useState(false);

  // Bulk selection — expected tab
  const [selectedExpected, setSelectedExpected] = useState<Set<string>>(
    new Set(),
  );
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

  // Bulk selection — actual tab
  const [selectedActual, setSelectedActual] = useState<Set<string>>(new Set());
  const [batchRemoveOpen, setBatchRemoveOpen] = useState(false);
  const [batchRemoving, setBatchRemoving] = useState(false);

  const expected = data?.expected ?? [];
  const actual = data?.actual ?? [];

  const hasExpectedSelection = selectedExpected.size > 0;
  const hasActualSelection = selectedActual.size > 0;

  // --- Selection helpers ---

  function toggleExpected(studentId: string) {
    setSelectedExpected((prev) => {
      const next = new Set(prev);
      if (next.has(studentId)) next.delete(studentId);
      else next.add(studentId);
      return next;
    });
  }

  function toggleAllExpected() {
    setSelectedExpected((prev) =>
      prev.size === expected.length
        ? new Set()
        : new Set(expected.map((e) => e.student_id)),
    );
  }

  function toggleActual(userId: string) {
    setSelectedActual((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  }

  function toggleAllActual() {
    setSelectedActual((prev) =>
      prev.size === actual.length
        ? new Set()
        : new Set(actual.map((a) => a.user_id)),
    );
  }

  function clearSelections() {
    setSelectedExpected(new Set());
    setSelectedActual(new Set());
  }

  function switchTab(tab: RosterTab) {
    setActiveTab(tab);
    clearSelections();
  }

  function switchClass(classId: string) {
    setSelectedClassId(classId);
    clearSelections();
  }

  // --- Handlers ---

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newId.trim() || !selectedClassId) return;
    setAdding(true);
    try {
      await rosterApi.add(selectedClassId, newId.trim());
      toast.success(`学号 ${newId.trim()} 已添加`);
      setNewId("");
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "添加失败");
    } finally {
      setAdding(false);
    }
  }

  async function handleBatchImport() {
    if (!selectedClassId) return;
    const ids = batchText
      .split(/[\n,，]/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (ids.length === 0) return;

    setImporting(true);
    setBatchResult(null);
    try {
      const result = await rosterApi.batchImport(selectedClassId, ids);
      setBatchResult(result);
      toast.success(`成功添加 ${result.added} 个学号`);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }

  async function handleDeleteExpected() {
    if (!deleteTarget || !selectedClassId) return;
    setDeleting(true);
    try {
      await rosterApi.delete(selectedClassId, deleteTarget);
      toast.success(`学号 ${deleteTarget} 已删除`);
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  async function handleBatchDelete() {
    if (!selectedClassId || selectedExpected.size === 0) return;
    setBatchDeleting(true);
    try {
      const result = await rosterApi.batchDelete(selectedClassId, [
        ...selectedExpected,
      ]);
      toast.success(`已删除 ${result.deleted} 个学号`);
      setSelectedExpected(new Set());
      setBatchDeleteOpen(false);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "批量删除失败");
    } finally {
      setBatchDeleting(false);
    }
  }

  async function handleResetPassword() {
    if (!resetTarget || !selectedClassId || !newPassword) return;
    setResetting(true);
    try {
      await rosterApi.resetPassword(
        selectedClassId,
        resetTarget.user_id,
        newPassword,
      );
      toast.success(`已重置 ${resetTarget.student_id} 的密码`);
      setResetTarget(null);
      setNewPassword("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "重置失败");
    } finally {
      setResetting(false);
    }
  }

  async function handleRemoveMember() {
    if (!removeTarget || !selectedClassId) return;
    setRemoving(true);
    try {
      await rosterApi.removeMember(selectedClassId, removeTarget.user_id);
      toast.success(`已将 ${removeTarget.student_id} 移出班级`);
      setRemoveTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "移除失败");
    } finally {
      setRemoving(false);
    }
  }

  async function handleBatchRemove() {
    if (!selectedClassId || selectedActual.size === 0) return;
    setBatchRemoving(true);
    try {
      const result = await rosterApi.batchRemoveMembers(selectedClassId, [
        ...selectedActual,
      ]);
      toast.success(`已移除 ${result.removed} 名学生`);
      setSelectedActual(new Set());
      setBatchRemoveOpen(false);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "批量移除失败");
    } finally {
      setBatchRemoving(false);
    }
  }

  // --- Toolbar right side (context-dependent) ---

  function renderToolbar() {
    if (activeTab === "expected" && hasExpectedSelection) {
      return (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            已选 {selectedExpected.size} 项
          </span>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
            onClick={() => setBatchDeleteOpen(true)}
          >
            <Trash2 className="mr-1 h-3.5 w-3.5" />
            批量删除
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedExpected(new Set())}
          >
            <X className="mr-1 h-3.5 w-3.5" />
            取消
          </Button>
        </div>
      );
    }

    if (activeTab === "actual" && hasActualSelection) {
      return (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            已选 {selectedActual.size} 项
          </span>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
            onClick={() => setBatchRemoveOpen(true)}
          >
            <UserMinus className="mr-1 h-3.5 w-3.5" />
            批量移除
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedActual(new Set())}
          >
            <X className="mr-1 h-3.5 w-3.5" />
            取消
          </Button>
        </div>
      );
    }

    if (activeTab === "expected") {
      return (
        <div className="flex items-center gap-2">
          <form onSubmit={handleAdd} className="flex items-center gap-2">
            <Input
              placeholder="输入学号"
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              className="w-36 h-8 text-sm"
            />
            <Button type="submit" size="sm" disabled={!newId.trim() || adding}>
              {adding ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="mr-1 h-3.5 w-3.5" />
              )}
              添加
            </Button>
          </form>
          <Dialog
            open={batchOpen}
            onOpenChange={(open) => {
              setBatchOpen(open);
              if (!open) {
                setBatchText("");
                setBatchResult(null);
              }
            }}
          >
            <DialogTrigger render={<Button variant="outline" size="sm" />}>
              <Upload className="mr-1 h-3.5 w-3.5" />
              批量导入
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  批量导入学号到「{selectedClass?.name}」
                </DialogTitle>
              </DialogHeader>
              <Textarea
                placeholder="每行一个学号，或用逗号分隔"
                rows={8}
                value={batchText}
                onChange={(e) => setBatchText(e.target.value)}
              />
              {batchResult && (
                <p className="text-sm text-muted-foreground">
                  成功添加 {batchResult.added} 个，跳过 {batchResult.duplicates}{" "}
                  个重复
                </p>
              )}
              <DialogFooter>
                <DialogClose render={<Button variant="outline" />}>
                  关闭
                </DialogClose>
                <Button
                  onClick={handleBatchImport}
                  disabled={!batchText.trim() || importing}
                >
                  {importing && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  导入
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      );
    }

    return null;
  }

  // --- Render ---

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Header: title + tab nav + class selector + toolbar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-heading font-semibold page-title-decorated">
            花名册
          </h1>

          {selectedClassId && !loading && !error && (
            <nav className="flex items-center gap-4">
              {(
                [
                  ["expected", "班级成员", expected.length],
                  ["actual", "实际注册", actual.length],
                ] as const
              ).map(([tab, label, count]) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => switchTab(tab)}
                  className={cn(
                    "relative pb-1 text-sm transition-colors",
                    activeTab === tab
                      ? "font-medium text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}({count})
                  {activeTab === tab && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--gold)] rounded-full" />
                  )}
                </button>
              ))}
            </nav>
          )}
        </div>

        <div className="flex items-center gap-3">
          <Select
            value={selectedClass?.name}
            onValueChange={(name) => {
              const found = classes.find((c) => c.name === name);
              if (found) switchClass(found.id);
            }}
          >
            <SelectTrigger className="w-48 h-8 text-sm">
              <SelectValue placeholder="选择班级" />
            </SelectTrigger>
            <SelectContent>
              {classes.map((c) => (
                <SelectItem key={c.id} value={c.name}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedClassId && !loading && !error && renderToolbar()}
        </div>
      </div>

      {/* Content */}
      {!selectedClassId ? (
        <EmptyState
          icon={<Users className="h-12 w-12" />}
          title="请先选择班级"
          description="在上方选择要管理花名册的班级"
        />
      ) : loading ? (
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-64 w-full rounded-lg" />
        </div>
      ) : error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : activeTab === "expected" ? (
        expected.length === 0 ? (
          <EmptyState
            icon={<Users className="h-10 w-10" />}
            title="暂无学号"
            description="通过上方输入框添加学号，或批量导入"
          />
        ) : (
          <Table className="data-table">
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={
                      selectedExpected.size === expected.length &&
                      expected.length > 0
                    }
                    onCheckedChange={toggleAllExpected}
                  />
                </TableHead>
                <TableHead>学号</TableHead>
                <TableHead>注册状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {expected.map((item) => (
                <TableRow key={item.student_id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedExpected.has(item.student_id)}
                      onCheckedChange={() => toggleExpected(item.student_id)}
                    />
                  </TableCell>
                  <TableCell>{item.student_id}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={
                        item.matched
                          ? "bg-success/10 text-success hover:bg-success/10"
                          : "bg-secondary text-muted-foreground hover:bg-secondary"
                      }
                    >
                      {item.matched ? "已注册" : "未注册"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteTarget(item.student_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )
      ) : actual.length === 0 ? (
        <EmptyState
          icon={<Users className="h-10 w-10" />}
          title="暂无学生"
          description="学生通过班级 Token 加入后将显示在此"
        />
      ) : (
        <Table className="data-table">
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={
                    selectedActual.size === actual.length && actual.length > 0
                  }
                  onCheckedChange={toggleAllActual}
                />
              </TableHead>
              <TableHead>学号</TableHead>
              <TableHead>姓名</TableHead>
              <TableHead>学院</TableHead>
              <TableHead>加入时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {actual.map((item) => (
              <TableRow key={item.user_id}>
                <TableCell>
                  <Checkbox
                    checked={selectedActual.has(item.user_id)}
                    onCheckedChange={() => toggleActual(item.user_id)}
                  />
                </TableCell>
                <TableCell>{item.student_id}</TableCell>
                <TableCell>{item.display_name ?? "-"}</TableCell>
                <TableCell>
                  {item.college
                    ? (COLLEGE_LABELS[item.college] ?? item.college)
                    : "-"}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(item.joined_at)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      title="重置密码"
                      onClick={() => setResetTarget(item)}
                    >
                      <KeyRound className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      title="移出班级"
                      onClick={() => setRemoveTarget(item)}
                    >
                      <UserMinus className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Dialogs */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="删除班级成员"
        description={`确定要从班级成员中删除学号 ${deleteTarget} 吗？这不会影响该学生的注册状态。`}
        confirmText="删除"
        onConfirm={handleDeleteExpected}
        loading={deleting}
      />

      <ConfirmDialog
        open={batchDeleteOpen}
        onOpenChange={setBatchDeleteOpen}
        title="批量删除班级成员"
        description={`确定要从班级成员中删除选中的 ${selectedExpected.size} 个学号吗？这不会影响已注册学生的账号。`}
        confirmText="删除"
        onConfirm={handleBatchDelete}
        loading={batchDeleting}
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
            <DialogTitle>
              重置密码 — {resetTarget?.student_id} {resetTarget?.display_name}
            </DialogTitle>
          </DialogHeader>
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
            <Button
              variant="outline"
              onClick={() => {
                setResetTarget(null);
                setNewPassword("");
              }}
            >
              取消
            </Button>
            <Button
              onClick={handleResetPassword}
              disabled={!newPassword || resetting}
            >
              {resetting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              确认重置
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!removeTarget}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        title="移出班级"
        description={`确定要将 ${removeTarget?.student_id}（${removeTarget?.display_name ?? "未知"}）移出班级吗？该学生在此班级中的所有提交记录将被删除，此操作不可撤销。`}
        confirmText="移除"
        onConfirm={handleRemoveMember}
        loading={removing}
      />

      <ConfirmDialog
        open={batchRemoveOpen}
        onOpenChange={setBatchRemoveOpen}
        title="批量移出班级"
        description={`确定要将选中的 ${selectedActual.size} 名学生移出班级吗？他们在此班级中的所有提交记录将被删除，此操作不可撤销。`}
        confirmText="移除"
        onConfirm={handleBatchRemove}
        loading={batchRemoving}
      />
    </div>
  );
}
