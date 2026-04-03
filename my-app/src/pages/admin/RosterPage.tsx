import { useState, type FormEvent } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Loader2, Plus, Upload, Trash2, Users } from "lucide-react";

export default function RosterPage() {
  const { classes } = useClassContext();

  // Selected class for this page (independent of global selector)
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const selectedClass = classes.find((c) => c.id === selectedClassId) ?? null;

  const { data, loading, error, refetch } = useApi(
    () => (selectedClassId ? rosterApi.list(selectedClassId) : Promise.resolve({ items: [], total: 0 })),
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

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; registered: boolean } | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  async function handleDelete() {
    if (!deleteTarget || !selectedClassId) return;
    setDeleting(true);
    try {
      await rosterApi.delete(selectedClassId, deleteTarget.id);
      toast.success(`学号 ${deleteTarget.id} 已删除`);
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-4 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold">学号名单</h1>

      {/* Class selector */}
      <Card>
        <CardContent className="pt-6">
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
                当前 {items.length} 人
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {!selectedClassId ? (
        <EmptyState
          icon={<Users className="h-12 w-12" />}
          title="请先选择班级"
          description="在上方选择要管理学号名单的班级"
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
          {/* Action bar */}
          <div className="flex flex-wrap items-center gap-3">
            <form onSubmit={handleAdd} className="flex items-center gap-2">
              <Input
                placeholder="输入学号"
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                className="w-48"
              />
              <Button type="submit" size="sm" disabled={!newId.trim() || adding}>
                {adding ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Plus className="mr-1 h-4 w-4" />}
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
                  <DialogTitle>批量导入学号到「{selectedClass?.name}」</DialogTitle>
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
                  <Button onClick={handleBatchImport} disabled={!batchText.trim() || importing}>
                    {importing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    导入
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {/* Roster table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                {selectedClass?.name} — 名单 ({items.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {items.length === 0 ? (
                <EmptyState
                  icon={<Users className="h-10 w-10" />}
                  title="暂无学号"
                  description="通过上方输入框添加学号，或批量导入"
                />
              ) : (
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>学号</TableHead>
                        <TableHead>注册状态</TableHead>
                        <TableHead className="text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {items.map((item) => (
                        <TableRow key={item.student_id}>
                          <TableCell>{item.student_id}</TableCell>
                          <TableCell>
                            <Badge
                              variant="secondary"
                              className={
                                item.registered
                                  ? "bg-green-50 text-green-700 hover:bg-green-50"
                                  : "bg-stone-100 text-stone-600 hover:bg-stone-100"
                              }
                            >
                              {item.registered ? "已注册" : "未注册"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => setDeleteTarget({ id: item.student_id, registered: item.registered })}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除"
        description={
          `确定要删除学号 ${deleteTarget?.id} 吗？` +
          (deleteTarget?.registered ? " 该学号已注册，删除后对应学生将无法登录。" : "")
        }
        confirmText="删除"
        onConfirm={handleDelete}
        loading={deleting}
      />
    </div>
  );
}
