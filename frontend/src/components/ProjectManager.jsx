import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { 
  FileText, 
  Folder, 
  FolderOpen,
  Plus,
  Edit,
  Trash2,
  Download,
  Upload,
  Search,
  RefreshCw,
  Save,
  X,
  Eye,
  Code,
  Image,
  File
} from 'lucide-react'

const FileExplorer = ({ workspaceFiles, onFileSelect, onFileAction }) => {
  const [selectedFile, setSelectedFile] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPath, setCurrentPath] = useState('/')
  const [expandedFolders, setExpandedFolders] = useState(new Set(['/']))

  const filteredFiles = workspaceFiles.filter(file => 
    file.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    file.path?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getFileIcon = (file) => {
    if (file.type === 'directory') {
      return expandedFolders.has(file.path) ? <FolderOpen className="h-4 w-4" /> : <Folder className="h-4 w-4" />
    }
    
    const extension = file.name.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'js':
      case 'jsx':
      case 'ts':
      case 'tsx':
      case 'py':
      case 'java':
      case 'cpp':
      case 'c':
        return <Code className="h-4 w-4" />
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'svg':
        return <Image className="h-4 w-4" />
      case 'txt':
      case 'md':
      case 'json':
      case 'xml':
      case 'html':
      case 'css':
        return <FileText className="h-4 w-4" />
      default:
        return <File className="h-4 w-4" />
    }
  }

  const handleFileClick = (file) => {
    if (file.type === 'directory') {
      const newExpanded = new Set(expandedFolders)
      if (expandedFolders.has(file.path)) {
        newExpanded.delete(file.path)
      } else {
        newExpanded.add(file.path)
      }
      setExpandedFolders(newExpanded)
    } else {
      setSelectedFile(file)
      onFileSelect?.(file)
    }
  }

  const handleFileAction = (action, file) => {
    onFileAction?.(action, file)
  }

  return (
    <div className="space-y-4">
      {/* 検索バー */}
      <div className="flex space-x-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="ファイルを検索..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline" onClick={() => onFileAction?.('refresh')}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* ツールバー */}
      <div className="flex space-x-2">
        <Button size="sm" variant="outline" onClick={() => onFileAction?.('new_file')}>
          <Plus className="h-4 w-4 mr-2" />
          新規ファイル
        </Button>
        <Button size="sm" variant="outline" onClick={() => onFileAction?.('new_folder')}>
          <Folder className="h-4 w-4 mr-2" />
          新規フォルダ
        </Button>
        <Button size="sm" variant="outline" onClick={() => onFileAction?.('upload')}>
          <Upload className="h-4 w-4 mr-2" />
          アップロード
        </Button>
      </div>

      {/* ファイルリスト */}
      <ScrollArea className="h-96">
        <div className="space-y-1">
          {filteredFiles.map((file, index) => (
            <div
              key={index}
              className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                selectedFile?.path === file.path ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50'
              }`}
              onClick={() => handleFileClick(file)}
            >
              <div className="flex items-center space-x-3 flex-1">
                {getFileIcon(file)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{file.name}</p>
                  <p className="text-sm text-gray-500 truncate">
                    {file.path} • {file.type}
                    {file.size && ` • ${file.size} bytes`}
                  </p>
                </div>
              </div>
              
              {file.type !== 'directory' && (
                <div className="flex space-x-1">
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFileAction('view', file)
                    }}
                  >
                    <Eye className="h-3 w-3" />
                  </Button>
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFileAction('edit', file)
                    }}
                  >
                    <Edit className="h-3 w-3" />
                  </Button>
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFileAction('download', file)
                    }}
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFileAction('delete', file)
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

const CodeEditor = ({ file, content, onChange, onSave, onClose }) => {
  const [editorContent, setEditorContent] = useState(content || '')
  const [isModified, setIsModified] = useState(false)

  useEffect(() => {
    setEditorContent(content || '')
    setIsModified(false)
  }, [content])

  const handleContentChange = (value) => {
    setEditorContent(value)
    setIsModified(value !== content)
    onChange?.(value)
  }

  const handleSave = () => {
    onSave?.(editorContent)
    setIsModified(false)
  }

  const getLanguage = (filename) => {
    const extension = filename.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'js':
      case 'jsx':
        return 'javascript'
      case 'ts':
      case 'tsx':
        return 'typescript'
      case 'py':
        return 'python'
      case 'html':
        return 'html'
      case 'css':
        return 'css'
      case 'json':
        return 'json'
      case 'md':
        return 'markdown'
      default:
        return 'text'
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* エディターヘッダー */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center space-x-3">
          <Code className="h-4 w-4" />
          <span className="font-medium">{file?.name}</span>
          {isModified && <Badge variant="secondary">未保存</Badge>}
        </div>
        <div className="flex space-x-2">
          <Button size="sm" onClick={handleSave} disabled={!isModified}>
            <Save className="h-4 w-4 mr-2" />
            保存
          </Button>
          <Button size="sm" variant="outline" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* エディター本体 */}
      <div className="flex-1 p-4">
        <textarea
          value={editorContent}
          onChange={(e) => handleContentChange(e.target.value)}
          className="w-full h-full font-mono text-sm border rounded-md p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="コードを入力してください..."
          spellCheck={false}
        />
      </div>

      {/* エディターフッター */}
      <div className="flex items-center justify-between p-3 border-t text-sm text-gray-500">
        <span>言語: {getLanguage(file?.name || '')}</span>
        <span>行数: {editorContent.split('\n').length}</span>
      </div>
    </div>
  )
}

const FileViewer = ({ file, content }) => {
  const getFileType = (filename) => {
    const extension = filename.split('.').pop()?.toLowerCase()
    
    if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(extension)) {
      return 'image'
    } else if (['mp4', 'webm', 'ogg'].includes(extension)) {
      return 'video'
    } else if (['pdf'].includes(extension)) {
      return 'pdf'
    } else {
      return 'text'
    }
  }

  const fileType = getFileType(file?.name || '')

  return (
    <div className="p-4">
      <div className="flex items-center space-x-3 mb-4">
        <Eye className="h-5 w-5" />
        <h3 className="text-lg font-medium">{file?.name}</h3>
      </div>

      <div className="border rounded-lg p-4">
        {fileType === 'image' && (
          <img 
            src={`/api/workspace/file/${file?.path}`} 
            alt={file?.name}
            className="max-w-full h-auto"
          />
        )}
        
        {fileType === 'video' && (
          <video 
            src={`/api/workspace/file/${file?.path}`} 
            controls
            className="max-w-full h-auto"
          />
        )}
        
        {fileType === 'pdf' && (
          <iframe 
            src={`/api/workspace/file/${file?.path}`}
            className="w-full h-96"
            title={file?.name}
          />
        )}
        
        {fileType === 'text' && (
          <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded overflow-auto max-h-96">
            {content}
          </pre>
        )}
      </div>
    </div>
  )
}

const ProjectManager = () => {
  const [activeTab, setActiveTab] = useState('explorer')
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [workspaceFiles, setWorkspaceFiles] = useState([
    {
      name: 'README.md',
      path: '/README.md',
      type: 'file',
      size: 1024
    },
    {
      name: 'src',
      path: '/src',
      type: 'directory'
    },
    {
      name: 'main.py',
      path: '/src/main.py',
      type: 'file',
      size: 2048
    },
    {
      name: 'utils.js',
      path: '/src/utils.js',
      type: 'file',
      size: 512
    },
    {
      name: 'data.csv',
      path: '/data.csv',
      type: 'file',
      size: 4096
    }
  ])

  const handleFileSelect = (file) => {
    setSelectedFile(file)
    // ファイル内容を読み込む（実際の実装では API を呼び出す）
    loadFileContent(file)
  }

  const loadFileContent = async (file) => {
    try {
      // 実際の実装では API を呼び出してファイル内容を取得
      const response = await fetch(`/api/workspace/file/${file.path}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (response.ok) {
        const content = await response.text()
        setFileContent(content)
      }
    } catch (error) {
      console.error('Failed to load file content:', error)
      setFileContent('ファイルの読み込みに失敗しました。')
    }
  }

  const handleFileAction = async (action, file) => {
    switch (action) {
      case 'view':
        setSelectedFile(file)
        setIsEditing(false)
        await loadFileContent(file)
        setActiveTab('viewer')
        break
      
      case 'edit':
        setSelectedFile(file)
        setIsEditing(true)
        await loadFileContent(file)
        setActiveTab('editor')
        break
      
      case 'download':
        // ダウンロード処理
        const link = document.createElement('a')
        link.href = `/api/workspace/file/${file.path}`
        link.download = file.name
        link.click()
        break
      
      case 'delete':
        if (confirm(`${file.name} を削除しますか？`)) {
          // 削除処理
          try {
            await fetch(`/api/workspace/file/${file.path}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
              }
            })
            // ファイルリストを更新
            setWorkspaceFiles(prev => prev.filter(f => f.path !== file.path))
          } catch (error) {
            console.error('Failed to delete file:', error)
          }
        }
        break
      
      case 'refresh':
        // ファイルリストを更新
        await loadWorkspaceFiles()
        break
      
      case 'new_file':
        // 新規ファイル作成ダイアログを表示
        const fileName = prompt('ファイル名を入力してください:')
        if (fileName) {
          await createNewFile(fileName)
        }
        break
      
      case 'new_folder':
        // 新規フォルダ作成ダイアログを表示
        const folderName = prompt('フォルダ名を入力してください:')
        if (folderName) {
          await createNewFolder(folderName)
        }
        break
      
      case 'upload':
        // ファイルアップロード処理
        const input = document.createElement('input')
        input.type = 'file'
        input.multiple = true
        input.onchange = (e) => handleFileUpload(e.target.files)
        input.click()
        break
    }
  }

  const loadWorkspaceFiles = async () => {
    try {
      const response = await fetch('/api/workspace/files', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setWorkspaceFiles(data.files || [])
      }
    } catch (error) {
      console.error('Failed to load workspace files:', error)
    }
  }

  const createNewFile = async (fileName) => {
    try {
      const response = await fetch('/api/workspace/file', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          path: `/${fileName}`,
          content: ''
        })
      })
      
      if (response.ok) {
        await loadWorkspaceFiles()
      }
    } catch (error) {
      console.error('Failed to create file:', error)
    }
  }

  const createNewFolder = async (folderName) => {
    try {
      const response = await fetch('/api/workspace/folder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          path: `/${folderName}`
        })
      })
      
      if (response.ok) {
        await loadWorkspaceFiles()
      }
    } catch (error) {
      console.error('Failed to create folder:', error)
    }
  }

  const handleFileUpload = async (files) => {
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      
      try {
        await fetch('/api/workspace/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        })
      } catch (error) {
        console.error('Failed to upload file:', error)
      }
    }
    
    await loadWorkspaceFiles()
  }

  const handleSaveFile = async (content) => {
    if (!selectedFile) return
    
    try {
      const response = await fetch(`/api/workspace/file/${selectedFile.path}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          content: content
        })
      })
      
      if (response.ok) {
        setFileContent(content)
        console.log('File saved successfully')
      }
    } catch (error) {
      console.error('Failed to save file:', error)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="explorer">エクスプローラー</TabsTrigger>
          <TabsTrigger value="editor" disabled={!selectedFile || !isEditing}>エディター</TabsTrigger>
          <TabsTrigger value="viewer" disabled={!selectedFile || isEditing}>ビューアー</TabsTrigger>
        </TabsList>

        <TabsContent value="explorer" className="flex-1">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>ワークスペース</CardTitle>
            </CardHeader>
            <CardContent>
              <FileExplorer
                workspaceFiles={workspaceFiles}
                onFileSelect={handleFileSelect}
                onFileAction={handleFileAction}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="editor" className="flex-1">
          <Card className="h-full">
            <CardContent className="p-0 h-full">
              {selectedFile && isEditing && (
                <CodeEditor
                  file={selectedFile}
                  content={fileContent}
                  onChange={setFileContent}
                  onSave={handleSaveFile}
                  onClose={() => setActiveTab('explorer')}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="viewer" className="flex-1">
          <Card className="h-full">
            <CardContent className="p-0 h-full">
              {selectedFile && !isEditing && (
                <FileViewer
                  file={selectedFile}
                  content={fileContent}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ProjectManager

