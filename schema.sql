-- tabelas do vetcare (mysql 5.7+ ou 8)
-- o programa cria tudo sozinho, mas dá pra rodar na mão também

create database if not exists clinica_vet
  character set utf8mb4 collate utf8mb4_unicode_ci;
use clinica_vet;

create table if not exists tutores (
  id int auto_increment primary key,
  nome varchar(100) not null,
  cpf char(11) not null unique,
  telefone varchar(11) not null,
  email varchar(100) not null,
  endereco varchar(150) not null default ''
);

create table if not exists veterinarios (
  id int auto_increment primary key,
  nome varchar(100) not null,
  crmv varchar(20) not null unique,
  especialidade varchar(60) not null,
  telefone varchar(11) not null,
  email varchar(100) not null
);

create table if not exists animais (
  id int auto_increment primary key,
  nome varchar(60) not null,
  especie varchar(20) not null,
  raca varchar(60) not null default '',
  idade int not null,
  peso decimal(6,2) not null,
  tutor_id int not null,
  foreign key (tutor_id) references tutores(id) on delete restrict
);

create table if not exists consultas (
  id int auto_increment primary key,
  animal_id int not null,
  veterinario_id int not null,
  data_hora datetime not null,
  tipo varchar(30) not null,
  valor decimal(8,2) not null,
  status varchar(20) not null default 'agendada',
  observacoes varchar(255) not null default '',
  foreign key (animal_id) references animais(id) on delete restrict,
  foreign key (veterinario_id) references veterinarios(id) on delete restrict
);
