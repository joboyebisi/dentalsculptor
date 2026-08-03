import { collection, addDoc, updateDoc, doc, deleteDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './config';

interface ModelData {
  name: string;
  description: string;
  modelUrl: string;
  ownerId: string;
  ownerName: string;
  visibility: 'public' | 'private';
}

export const shareModel = async (modelData: ModelData) => {
  try {
    const modelsRef = collection(db, 'models');
    const docRef = await addDoc(modelsRef, {
      ...modelData,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp(),
    });
    return docRef.id;
  } catch (error) {
    console.error('Error sharing model:', error);
    throw error;
  }
};

export const updateModel = async (modelId: string, updates: Partial<ModelData>) => {
  try {
    const modelRef = doc(db, 'models', modelId);
    await updateDoc(modelRef, {
      ...updates,
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    console.error('Error updating model:', error);
    throw error;
  }
};

export const deleteModel = async (modelId: string) => {
  try {
    const modelRef = doc(db, 'models', modelId);
    await deleteDoc(modelRef);
  } catch (error) {
    console.error('Error deleting model:', error);
    throw error;
  }
}; 