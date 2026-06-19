import { useState } from 'react'
import Layout from './components/Layout'
import ApiExplorer from './components/ApiExplorer'
import ApiTester from './components/ApiTester'
import TestHistory from './components/TestHistory'
import Environments from './components/Environments'
import FileUploads from './components/FileUploads'

export default function App() {
  const [activeTab, setActiveTab] = useState('explorer')

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'explorer' && <ApiExplorer />}
      {activeTab === 'tester' && <ApiTester />}
      {activeTab === 'history' && <TestHistory />}
      {activeTab === 'environments' && <Environments />}
      {activeTab === 'uploads' && <FileUploads />}
    </Layout>
  )
}
