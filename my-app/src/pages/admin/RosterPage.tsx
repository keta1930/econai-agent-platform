import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
import { useApi } from "@/hooks/useApi";
import { rosterApi } from "@/api/roster";
import { toast } from "sonner";
import { Loader2, Plus, Upload, Trash2 } from "lucide-react";

export default function RosterPage() {
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useApi(() => rosterApi.list(), []);

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
    if (!newId.trim()) return;
    setAdding(true);
    try {
      await rosterApi.add(newId.trim());
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
    const ids = batchText
      .split(/[\n,，]/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (ids.length === 0) return;

    setImporting(true);
    setBatchResult(null);
    try {
      const result = await rosterApi.batchImport(ids);
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
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await rosterApi.delete(deleteTarget.id);
      toast.success(`学号 ${deleteTarget.id} 已删除`);
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
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">学号名单</h1>

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
              <DialogTitle>批量导入学号</DialogTitle>
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
          <CardTitle className="text-lg">名单 ({items.length})</CardTitle>
        </CardHeader>
        <CardContent>
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
                    <TableCell>
                      {item.registered ? (
                        <button
                          className="text-primary hover:underline font-medium"
                          onClick={() => navigate(`/admin/students/${item.student_id}`)}
                        >
                          {item.student_id}
                        </button>
                      ) : (
                        item.student_id
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={
                          item.registered
                            ? "bg-green-50 text-green-700 hover:bg-green-50"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-100"
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
        </CardContent>
      </Card>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm">
            确定要删除学号 <strong>{deleteTarget?.id}</strong> 吗？
          </p>
          {deleteTarget?.registered && (
            <p className="text-sm text-warning">该学号已注册，删除后对应学生将无法登录。</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
