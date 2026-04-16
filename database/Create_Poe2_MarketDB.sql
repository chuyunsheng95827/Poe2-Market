-- ====================================================================
-- 终极数据库创建脚本 for POE2MarketDB_2
-- 版本: 2.0 (类表继承模式)
-- ====================================================================

-- 1. 创建数据库
CREATE DATABASE Poe2_MarketDB;
GO

-- 2. 切换到数据库的上下文
USE Poe2_MarketDB;
GO

-- 3. 创建字典表 (Users & Currencies)
PRINT '正在创建 Users 和 Currencies 表...';
CREATE TABLE Users (
    UserID INT PRIMARY KEY IDENTITY(1,1),
    UserName NVARCHAR(100) NOT NULL UNIQUE
);
GO
CREATE TABLE Currencies (
    CurrencyID INT PRIMARY KEY IDENTITY(1,1),
    CurrencyName NVARCHAR(100) NOT NULL UNIQUE
);
GO

-- 技能表
CREATE TABLE Skills (
    SkillID INT PRIMARY KEY IDENTITY(1,1),
    SkillName NVARCHAR(255) NOT NULL UNIQUE
);
GO

-- 物品类别表
CREATE TABLE ItemCategories (
    CategoryID INT PRIMARY KEY IDENTITY(1,1),
    CategoryName NVARCHAR(50) NOT NULL UNIQUE
);
GO

-- 4. 创建核心公共物品表 (Items)
PRINT '正在创建核心 Items 表...';
CREATE TABLE Items (
    ItemID NVARCHAR(255) PRIMARY KEY,
    ItemName NVARCHAR(255) NOT NULL,
    BaseType NVARCHAR(100) NOT NULL,
    -- 用于判断属于哪个扩展表, e.g., 'Spear', 'Helmet'
    ItemImageURL NVARCHAR(MAX),
    
    -- 新增的状态列
    Quality INT,
    IsCorrupted BIT NOT NULL DEFAULT 0, -- 0 = 未腐化, 1 = 已腐化
    -- GrantedSkill NVARCHAR(255), -- 存放自带的技能名称 
    
    -- 基础需求属性
    ItemLevel INT,
    RequiredLevel INT,
    RequiredStr INT,
    RequiredDex INT,
    RequiredInt INT,
    
    -- 交易信息
    PriceAmount DECIMAL(18, 2) NOT NULL,
    ListedAtText NVARCHAR(100),
    UserID INT NOT NULL FOREIGN KEY REFERENCES Users(UserID),
    CurrencyID INT NOT NULL FOREIGN KEY REFERENCES Currencies(CurrencyID),
    SkillID INT NULL FOREIGN KEY REFERENCES Skills(SkillID), 
    CategoryID INT NOT NULL FOREIGN KEY REFERENCES ItemCategories(CategoryID) 
);
GO

-- 5. 创建扩展表 (存放专属属性)
PRINT '正在创建专属属性扩展表...';
-- 武器专属属性
CREATE TABLE WeaponProperties (
    ItemID NVARCHAR(255) PRIMARY KEY,
    PhysicalDmgMin INT,
    PhysicalDmgMax INT,
    ColdDmgMin INT,
    ColdDmgMax INT,
    FireDmgMin INT,
    FireDmgMax INT,
    LightningDmgMin INT,
    LightningDmgMax INT,
    ChaosDmgMin INT,
    ChaosDmgMax INT,
    CritChance DECIMAL(5, 2),
    AttacksPerSecond DECIMAL(5, 2),
    ReloadTime DECIMAL(5, 2), -- 十字弓专属
    Spirit INT, -- 权杖专属
    CONSTRAINT FK_Weapon_Items FOREIGN KEY (ItemID) REFERENCES Items(ItemID) ON DELETE CASCADE
);
GO
-- 护甲专属属性 (包含头、胸、手、鞋)
CREATE TABLE ArmorProperties (
    ItemID NVARCHAR(255) PRIMARY KEY,
    Armour INT,
    Evasion INT,
    EnergyShield INT,
    CONSTRAINT FK_Armor_Items FOREIGN KEY (ItemID) REFERENCES Items(ItemID) ON DELETE CASCADE
);
GO
-- 盾牌专属属性
CREATE TABLE ShieldProperties (
    ItemID NVARCHAR(255) PRIMARY KEY,
    BlockChance DECIMAL(5, 2),
    CONSTRAINT FK_Shield_Items FOREIGN KEY (ItemID) REFERENCES Items(ItemID) ON DELETE CASCADE
);
GO

-- 6. 创建全新的词缀表 (Affixes)
PRINT '正在创建 Affixes 表...';
CREATE TABLE Affixes (
    AffixID BIGINT PRIMARY KEY IDENTITY(1,1),
    ItemID NVARCHAR(255) NOT NULL,
    AffixText NVARCHAR(MAX) NOT NULL,
    AffixType NVARCHAR(20) NOT NULL, -- 'Implicit', 'Explicit', 'Enchant', 'Rune', 'Corrupted'
    CONSTRAINT FK_Affixes_Items FOREIGN KEY (ItemID) REFERENCES Items(ItemID) ON DELETE CASCADE
);
GO

PRINT '*** POE2_MarketDB 数据库及所有表已成功创建！ ***';

-- 测试时用于删除信息
DELETE FROM Affixes;
DELETE FROM ArmorProperties;
DELETE FROM Items;
DELETE FROM ShieldProperties;
DELETE FROM Users;
DELETE FROM WeaponProperties;
DELETE FROM Currencies;

-- 重置自增ID (可选)
DBCC CHECKIDENT ('Users', RESEED, 0);
DBCC CHECKIDENT ('Currencies', RESEED, 0);
DBCC CHECKIDENT ('Affixes', RESEED, 0);
DBCC CHECKIDENT ('ArmorProperties', RESEED, 0);
DBCC CHECKIDENT ('Items', RESEED, 0);
DBCC CHECKIDENT ('ShieldProperties', RESEED, 0);
DBCC CHECKIDENT ('WeaponProperties', RESEED, 0);