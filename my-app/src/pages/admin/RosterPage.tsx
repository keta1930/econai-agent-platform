import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
import { Loader2, Plus, Upload, Trash2, Users, KeyRound, UserMinus } from "lucide-react";
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

  // Single add state
  const [newId, setNewId] = useState("");
  const [adding, setAdding] = useState(false);

  // Batch import state
  const [batchText, setBatchText] = useState("");
  const [batchOpen, setBatchOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [batchResult, setBatchResult] = useState<{ added: number; duplicates: number } | null>(null);

  // Delete expected roster entry
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Reset password
  const [resetTarget, setResetTarget] = useState<ActualRosterItem | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetting, setResetting] = useState(false);

  // Remove member
  const [removeTarget, setRemoveTarget] = useState<ActualRosterItem | null>(null);
  const [removing, setRemoving] = useState(false);

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
      toast.success(`学号 ${deleteTarget} 已从班级成员中移除`);
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  async function handleResetPassword() {
    if (!resetTarget || !selectedClassId || !newPassword) return;
    setResetting(true);
    try {
      await rosterApi.resetPassword(selectedClassId, resetTarget.user_id, newPassword);
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

  const expected = data?.expected ?? [];
  const actual = data?.actual ?? [];

  return (
    <div className="space-y-4 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold page-title-decorated">花名册</h1>

      {/* Class selector */}
      <div className="flex items-center gap-3">
        <Label className="shrink-0 font-medium">选择班级</Label>
        <Select
          value={selectedClass?.name}
          onValueChange={(name) => {
            const found = classes.find((c) => c.name === name);
            if (found) setSelectedClassId(found.id);
          }}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="请选择要管理的班级" />
          </SelectTrigger>
          <SelectContent>
            {classes.map((c) => (
              <SelectItem key={c.id} value={c.name}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selectedClass && (
          <span className="text-sm text-muted-foreground">
            班级成员 {expected.length} 人 / 实际注册 {actual.length} 人
          </span>
        )}
      </div>

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
      ) : (
        <>
          {/* Tab switcher */}
          <div className="flex rounded-lg border border-border p-1 w-fit">
            <button
              type="button"
              className={cn(
                "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
                activeTab === "expected"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => setActiveTab("expected")}
            >
              班级成员 ({expected.length})
            </button>
            <button
              type="button"
              className={cn(
                "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
                activeTab === "actual"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => setActiveTab("actual")}
            >
              实际注册 ({actual.length})
            </button>
          </div>

          {/* Expected roster tab */}
          {activeTab === "expected" && (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <form onSubmit={handleAdd} className="flex items-center gap-2">
                  <Input
                    placeholder="输入学号"
                    value={newId}
                    onChange={(e) => setNewId(e.target.value)}
                    className="w-48"
                  />
                  <Button type="submit" size="sm" disabled={!newId.trim() || adding}>
                    {adding ? (
                      <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="mr-1 h-4 w-4" />
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
                    <Upload className="mr-1 h-4 w-4" />
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
                        成功添加 {batchResult.added} 个，跳过 {batchResult.duplicates} 个重复
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
                        {importing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        导入
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>

              {expected.length === 0 ? (
                <EmptyState
                  icon={<Users className="h-10 w-10" />}
                  title="暂无学号"
                  description="通过上方输入框添加学号，或批量导入"
                />
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    共 {expected.length} 人 — 已注册{" "}
                    {expected.filter((i) => i.matched).length} / 未注册{" "}
                    {expected.filter((i) => !i.matched).length}
                  </p>
                  <Table className="data-table">
                    <TableHeader>
                      <TableRow>
                        <TableHead>学号</TableHead>
                        <TableHead>注册状态</TableHead>
                        <TableHead className="text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {expected.map((item) => (
                        <TableRow key={item.student_id}>
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
                </>
              )}
            </>
          )}

          {/* Actual roster tab */}
          {activeTab === "actual" && (
            <>
              {actual.length === 0 ? (
                <EmptyState
                  icon={<Users className="h-10 w-10" />}
                  title="暂无学生"
                  description="学生通过班级 Token 加入后将显示在此"
                />
              ) : (
                <Table className="data-table">
                  <TableHeader>
                    <TableRow>
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
                        <TableCell>{item.student_id}</TableCell>
                        <TableCell>{item.display_name ?? "-"}</TableCell>
                        <TableCell>
                          {item.college ? (COLLEGE_LABELS[item.college] ?? item.college) : "-"}
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
            </>
          )}
        </>
      )}

      {/* Delete expected roster entry */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="删除班级成员"
        description={`确定要从班级成员中删除学号 ${deleteTarget} 吗？这不会影响该学生的注册状态。`}
        confirmText="删除"
        onConfirm={handleDeleteExpected}
        loading={deleting}
      />

      {/* Reset password dialog */}
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

      {/* Remove member confirm */}
      <ConfirmDialog
        open={!!removeTarget}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        title="移出班级"
        description={`确定要将 ${removeTarget?.student_id}（${removeTarget?.display_name ?? "未知"}）移出班级吗？该学生在此班级中的所有提交记录将被删除，此操作不可撤销。`}
        confirmText="移除"
        onConfirm={handleRemoveMember}
        loading={removing}
      />
    </div>
  );
}
